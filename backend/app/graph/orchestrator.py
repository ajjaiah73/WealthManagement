"""The advisory pipeline as a LangGraph StateGraph over AdvisoryState.

    START -> intent -> retrieval -> synthesis -> compliance --(not REJECTED)--> narrate -> END
                                       ^             |
                                       |      (REJECTED, iteration < MAX)
                                       +-- critique <+
                                                     |
                                      (REJECTED, iteration == MAX) --> escalate -> END

Every node writes an append-only audit event as it completes, and the case
record is persisted after every superstep, so the SSE endpoint can stream real
progress while the graph is still running. Compliance is deterministic/Z3 and
authoritative: the routing decision after `compliance` reads only the rule
engine's verdict, and the narrator runs strictly after that verdict is final.
"""
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.domain.advisory import AdvisoryCase, AdvisoryCaseRecord, CaseStatus
from app.domain.audit import AuditEvent
from app.domain.client import ClientProfile, build_fact_find
from app.domain.compliance import ComplianceResult, ComplianceStatus
from app.domain.product import Product
from app.domain.retrieval import RetrievedDocument
from app.graph.state import AdvisoryState, ExecutionMetadata, UserIntent
from app.repositories.base import AuditSink, CaseStore
from app.repositories.case_repository import InMemoryCaseRepository
from app.retrieval.graph import topic_label
from app.services.advisory_service import AdvisorySynthesisService
from app.services.compliance_service import ComplianceService
from app.services.llm_service import PROMPT_VERSION, LLMIntentExtractor, LLMNarrator
from app.services.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 3
RETRIEVAL_TOP_K = 6
DEFAULT_REQUEST = "Recommend a superannuation strategy"

TERMINAL_STATUSES = {CaseStatus.COMPLIANT, CaseStatus.WARNING, CaseStatus.REQUIRES_HUMAN_REVIEW}


def new_case_id() -> str:
    return f"CASE-{uuid.uuid4().hex[:8].upper()}"


@dataclass
class AdvisoryPipeline:
    retrieval_service: RetrievalService
    synthesis_service: AdvisorySynthesisService
    compliance_service: ComplianceService
    audit_repository: AuditSink
    case_repository: CaseStore
    intent_extractor: LLMIntentExtractor | None = None
    narrator: LLMNarrator | None = None
    max_iterations: int = MAX_ITERATIONS
    _graph: CompiledStateGraph | None = field(default=None, init=False, repr=False)

    # ----------------------------------------------------------------- graph
    @property
    def graph(self) -> CompiledStateGraph:
        if self._graph is None:
            self._graph = self._build_graph()
        return self._graph

    def _build_graph(self) -> CompiledStateGraph:
        g = StateGraph(AdvisoryState)
        g.add_node("intent", self._intent_node)
        g.add_node("retrieval", self._retrieval_node)
        g.add_node("synthesis", self._synthesis_node)
        g.add_node("compliance", self._compliance_node)
        g.add_node("critique", self._critique_node)
        g.add_node("escalate", self._escalate_node)
        g.add_node("narrate", self._narrate_node)
        g.add_edge(START, "intent")
        g.add_edge("intent", "retrieval")
        g.add_edge("retrieval", "synthesis")
        g.add_edge("synthesis", "compliance")
        g.add_conditional_edges(
            "compliance", self._route_after_compliance,
            {"narrate": "narrate", "critique": "critique", "escalate": "escalate"},
        )
        g.add_edge("critique", "synthesis")
        g.add_edge("escalate", END)
        g.add_edge("narrate", END)
        return g.compile()

    def mermaid(self) -> str:
        return self.graph.get_graph().draw_mermaid()

    # ------------------------------------------------------------- execution
    def create_case(self, profile: ClientProfile, request: str, case_id: str | None = None) -> AdvisoryCaseRecord:
        now = datetime.now(UTC)
        record = AdvisoryCaseRecord(
            case=AdvisoryCase(
                case_id=case_id or new_case_id(), client_id=profile.client_id, status=CaseStatus.IN_PROGRESS,
                iteration_count=0, recommendation=None, created_at=now, updated_at=now,
            ),
            request=request,
            current_step="queued",
        )
        return self.case_repository.save(record)

    def execute(
        self, record: AdvisoryCaseRecord, profile: ClientProfile, products: list[Product], session_id: str
    ) -> AdvisoryCaseRecord:
        case = record.case
        initial = AdvisoryState(
            client_profile=profile,
            user_intent=UserIntent(raw_request=record.request or DEFAULT_REQUEST),
            execution_metadata=ExecutionMetadata(
                session_id=session_id, case_id=case.case_id,
                started_at=case.created_at, updated_at=case.created_at,
            ),
        )
        state = initial
        # Per-run inputs travel in the run config, not on this (shared, thread-safe) pipeline.
        config: RunnableConfig = {"recursion_limit": 50, "configurable": {"products": products}}
        try:
            for values in self.graph.stream(initial, config=config, stream_mode="values"):
                state = AdvisoryState.model_validate(values)
                record = self._save_progress(record, state, final=False)
            record = self._save_progress(record, state)
        except Exception as exc:
            logger.exception("Advisory pipeline failed for %s", case.case_id)
            self._log(state, "orchestrator", "pipeline_error", "failure",
                      details=f"{type(exc).__name__}: pipeline aborted; escalated to human review")
            state = state.model_copy(update={"status": CaseStatus.REQUIRES_HUMAN_REVIEW, "current_step": "error"})
            record = self._save_progress(record, state)
        return record

    def _save_progress(
        self, record: AdvisoryCaseRecord, state: AdvisoryState, final: bool = True
    ) -> AdvisoryCaseRecord:
        # Compliance decides the status before the narrate node rewrites the rationale.
        # Readers (SSE `done`, GET) treat a terminal status as "finished", so it is only
        # persisted once the whole graph has run.
        status = state.status
        if not final and status in TERMINAL_STATUSES:
            status = CaseStatus.IN_PROGRESS
        recommendation = state.final_advice or state.selected_strategy
        updated = AdvisoryCaseRecord(
            case=record.case.model_copy(update={
                "status": status,
                "iteration_count": state.iteration_count,
                "recommendation": recommendation,
                "updated_at": datetime.now(UTC),
            }),
            compliance_history=state.compliance_results,
            critique_notes=state.critique_notes,
            retrieved_documents=state.retrieved_documents,
            request=state.user_intent.raw_request,
            goal=state.user_intent.goal,
            constraints=state.user_intent.constraints,
            retrieval_query=state.user_intent.retrieval_query,
            graph_context=state.graph_context,
            current_step=state.current_step,
        )
        return self.case_repository.save(updated)

    # ------------------------------------------------------------------ nodes
    def _log(
        self, state: AdvisoryState, agent: str, action: str, status: str, details: str | None = None,
        model: str | None = None, iteration: int | None = None,
    ) -> str:
        meta = state.execution_metadata
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(UTC),
            session_id=meta.session_id,
            client_id=state.client_profile.client_id,
            case_id=meta.case_id,
            agent=agent,
            action=action,
            model=model,
            prompt_version=PROMPT_VERSION if model else None,
            input_reference=f"case:{meta.case_id}/iteration:{state.iteration_count}",
            iteration=state.iteration_count if iteration is None else iteration,
            status=status,
            details=details,
        )
        self.audit_repository.append(event)
        return event.event_id

    def _intent_node(self, state: AdvisoryState) -> dict[str, Any]:
        profile = state.client_profile
        request = state.user_intent.raw_request
        missing = build_fact_find(profile).missing_fields
        extracted = self.intent_extractor.extract(profile, request) if self.intent_extractor else None
        if extracted is not None:
            intent = UserIntent(raw_request=request, method="llm", **extracted)
            model = self.intent_extractor.model if self.intent_extractor else None
        else:
            goals = "; ".join(profile.financial_goals)
            intent = UserIntent(
                raw_request=request,
                goal=f"{request.rstrip('.')}" + (f" (client goals: {goals})" if goals else ""),
                constraints=list(profile.constraints),
                retrieval_query=request,
                method="deterministic",
            )
            model = None
        if missing:
            intent.constraints = [*intent.constraints, f"Fact-find incomplete: missing {', '.join(missing)}"]
        event_id = self._log(
            state, "intent_agent", "extract_intent", "success", model=model,
            details=f"[{intent.method}] goal: {intent.goal}"
            + (f" | missing fact-find fields: {', '.join(missing)}" if missing else ""),
        )
        return {"user_intent": intent, "audit_events": [*state.audit_events, event_id], "current_step": "intent"}

    def _retrieval_node(self, state: AdvisoryState) -> dict[str, Any]:
        query = state.user_intent.retrieval_query or state.user_intent.raw_request
        retrieved, trace = self.retrieval_service.retrieve_with_trace(state.client_profile, query, RETRIEVAL_TOP_K)
        graph_context = [f"{topic_label(k)}: {reason}" for k, reason in trace.topics.items()]
        event_id = self._log(
            state, "retrieval_agent", "hybrid_retrieval", "success",
            details=f"retrieved {len(retrieved)} documents ({trace.summary()})",
        )
        return {
            "retrieved_documents": retrieved,
            "graph_context": graph_context,
            "audit_events": [*state.audit_events, event_id],
            "current_step": "retrieval",
        }

    def _synthesis_node(self, state: AdvisoryState, config: RunnableConfig) -> dict[str, Any]:
        iteration = state.iteration_count + 1
        products: list[Product] = config["configurable"]["products"]
        outcome = self.synthesis_service.synthesize_with_meta(
            state.client_profile, products, state.retrieved_documents, state.critique_notes,
            goal=state.user_intent.goal,
        )
        rec = outcome.recommendation
        event_id = self._log(
            state, "advisory_synthesis_agent", "synthesize_strategy", "success", model=outcome.model,
            iteration=iteration,
            details=f"[{outcome.method}] selected {rec.product_id} ({rec.product_type}, {rec.allocation}, "
                    f"fee {rec.fee_percentage:.2f}%) from {len(outcome.candidate_ids)} eligible products",
        )
        return {
            "iteration_count": iteration,
            "selected_strategy": rec,
            "candidate_strategies": [*state.candidate_strategies, rec],
            "audit_events": [*state.audit_events, event_id],
            "current_step": "synthesis",
        }

    def _compliance_node(self, state: AdvisoryState) -> dict[str, Any]:
        assert state.selected_strategy is not None
        result: ComplianceResult = self.compliance_service.evaluate(
            state.execution_metadata.case_id, state.client_profile, state.selected_strategy
        )
        rejected = result.status == ComplianceStatus.REJECTED
        event_id = self._log(
            state, "compliance_agent", "verify_compliance", "failure" if rejected else "success",
            details=result.status.value,
        )
        return {
            "compliance_results": [*state.compliance_results, result],
            "status": CaseStatus.REJECTED if rejected else CaseStatus(result.status.value),
            "audit_events": [*state.audit_events, event_id],
            "current_step": "compliance",
        }

    def _route_after_compliance(self, state: AdvisoryState) -> str:
        latest = state.compliance_results[-1]
        if latest.status != ComplianceStatus.REJECTED:
            return "narrate"
        return "critique" if state.iteration_count < self.max_iterations else "escalate"

    def _critique_node(self, state: AdvisoryState) -> dict[str, Any]:
        latest = state.compliance_results[-1]
        failed = [r.detail for r in latest.rule_results if not r.passed and not r.is_warning]
        event_id = self._log(
            state, "compliance_agent", "structured_critique", "success", details="; ".join(failed)
        )
        return {
            "critique_notes": [*state.critique_notes, *failed],
            "audit_events": [*state.audit_events, event_id],
            "current_step": "critique",
        }

    def _escalate_node(self, state: AdvisoryState) -> dict[str, Any]:
        event_id = self._log(
            state, "compliance_agent", "max_iterations_reached", "failure", details="Escalated to human review"
        )
        return {
            "status": CaseStatus.REQUIRES_HUMAN_REVIEW,
            "audit_events": [*state.audit_events, event_id],
            "current_step": "escalated",
        }

    def _narrate_node(self, state: AdvisoryState) -> dict[str, Any]:
        # Neuro-symbolic split: compliance status is already final; the LLM only
        # writes the client-facing rationale and can never alter the outcome.
        rec = state.selected_strategy
        update: dict[str, Any] = {"final_advice": rec, "current_step": "complete"}
        if self.narrator is not None and rec is not None:
            text = self.narrator.write_rationale(
                state.client_profile, rec, state.retrieved_documents, state.critique_notes
            )
            if text is not None:
                update["final_advice"] = rec.model_copy(update={"rationale": text})
                event_id = self._log(
                    state, "advisory_synthesis_agent", "llm_narrative", "success",
                    details="Rationale written by LLM", model=self.narrator.model,
                )
                update["audit_events"] = [*state.audit_events, event_id]
        return update


# --------------------------------------------------------------------------------------
# Synchronous convenience wrapper (unit tests / scripts).


class AdvisoryRunResult:
    def __init__(
        self,
        case: AdvisoryCase,
        compliance_history: list[ComplianceResult],
        retrieved_documents: list[RetrievedDocument],
        critique_notes: list[str],
    ) -> None:
        self.case = case
        self.compliance_history = compliance_history
        self.retrieved_documents = retrieved_documents
        self.critique_notes = critique_notes


def run_advisory_case(
    profile: ClientProfile,
    products: list[Product],
    retrieval_service: RetrievalService,
    advisory_service: AdvisorySynthesisService,
    compliance_service: ComplianceService,
    audit_repository: AuditSink,
    session_id: str,
    query: str = DEFAULT_REQUEST,
    narrator: LLMNarrator | None = None,
    case_repository: CaseStore | None = None,
    intent_extractor: LLMIntentExtractor | None = None,
) -> AdvisoryRunResult:
    pipeline = AdvisoryPipeline(
        retrieval_service=retrieval_service,
        synthesis_service=advisory_service,
        compliance_service=compliance_service,
        audit_repository=audit_repository,
        case_repository=case_repository or InMemoryCaseRepository(),
        intent_extractor=intent_extractor,
        narrator=narrator,
    )
    record = pipeline.execute(pipeline.create_case(profile, query), profile, products, session_id)
    return AdvisoryRunResult(record.case, record.compliance_history, record.retrieved_documents,
                             record.critique_notes)
