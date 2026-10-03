from typing import Any

from fastapi.testclient import TestClient

from app.domain.advisory import CaseStatus
from app.domain.client import ClientProfile
from app.domain.product import Product, ProductType
from app.domain.retrieval import RetrievedDocument
from app.graph.orchestrator import AdvisoryPipeline
from app.main import app
from app.mock_data.clients import SEED_CLIENTS
from app.mock_data.products import SEED_PRODUCTS
from app.repositories.audit_repository import InMemoryAuditRepository
from app.repositories.case_repository import InMemoryCaseRepository
from app.repositories.document_repository import InMemoryDocumentRepository
from app.services.advisory_service import AdvisorySynthesisService, eligible_products
from app.services.compliance_service import ComplianceService
from app.services.retrieval_service import MockRetrievalService

CLIENTS = {c.client_id: c for c in SEED_CLIENTS}
api = TestClient(app)


class FakeSynthesisLLM:
    """Stands in for LLMSynthesisAdvisor; records what it was offered."""

    model = "fake-model"

    def __init__(self, pick: str | None) -> None:
        self.pick = pick
        self.calls: list[dict[str, Any]] = []

    def choose(self, profile: ClientProfile, goal: str | None, candidates: list[Product],
               retrieved: list[RetrievedDocument], critique_notes: list[str]) -> dict[str, Any] | None:
        self.calls.append({"candidates": [p.product_id for p in candidates], "critique": list(critique_notes)})
        if self.pick is None:
            return None
        reasoning = f"LLM chose {self.pick} [DOC-017]"
        return {"product_id": self.pick, "reasoning": reasoning, "risks": ["Sequencing risk"]}


def _pipeline(
    llm: FakeSynthesisLLM | None, demo_mode: bool = True
) -> tuple[AdvisoryPipeline, InMemoryAuditRepository]:
    audit = InMemoryAuditRepository()
    pipeline = AdvisoryPipeline(
        retrieval_service=MockRetrievalService(InMemoryDocumentRepository([])),
        synthesis_service=AdvisorySynthesisService(llm=llm, demo_mode=demo_mode),  # type: ignore[arg-type]
        compliance_service=ComplianceService(),
        audit_repository=audit,
        case_repository=InMemoryCaseRepository(),
    )
    return pipeline, audit


def _run(pipeline: AdvisoryPipeline, client_id: str):  # type: ignore[no-untyped-def]
    profile = CLIENTS[client_id]
    record = pipeline.create_case(profile, "Recommend a strategy")
    return pipeline.execute(record, profile, list(SEED_PRODUCTS), "s")


def test_graph_is_a_compiled_langgraph_with_self_correction_loop() -> None:
    pipeline, _ = _pipeline(None)
    nodes = set(pipeline.graph.get_graph().nodes)
    assert {"intent", "retrieval", "synthesis", "compliance", "critique", "escalate", "narrate"} <= nodes
    mermaid = pipeline.mermaid()
    assert "critique" in mermaid and "synthesis" in mermaid


def test_llm_choice_is_used_but_cannot_override_compliance() -> None:
    # LLM insists on an 80/20 product for a 58-year-old retiring at 60 (non-demo, no pins):
    # compliance rejects it every time, so the case must escalate, not pass.
    llm = FakeSynthesisLLM(pick="P-001")
    pipeline, audit = _pipeline(llm, demo_mode=False)
    record = _run(pipeline, "C-0002")
    assert record.case.status == CaseStatus.REQUIRES_HUMAN_REVIEW
    assert record.case.iteration_count == 3
    assert len(llm.calls) == 3 and llm.calls[1]["critique"]  # critique fed back to the LLM
    synth = [e for e in audit.list_for_case(record.case.case_id) if e.action == "synthesize_strategy"]
    assert all(e.details and e.details.startswith("[llm]") and e.model == "fake-model" for e in synth)


def test_llm_correction_after_critique_reaches_compliant() -> None:
    llm = FakeSynthesisLLM(pick="P-010")  # 30/70 conservative choice
    pipeline, _ = _pipeline(llm, demo_mode=True)
    record = _run(pipeline, "C-0002")  # demo pin P-001 first -> rejected -> LLM corrects
    assert record.case.status == CaseStatus.COMPLIANT
    assert record.case.iteration_count == 2
    assert record.case.recommendation is not None
    assert record.case.recommendation.product_id == "P-010"
    assert record.case.recommendation.allocation == "30/70"  # copied from catalogue, not generated
    assert "LLM chose P-010" in record.case.recommendation.rationale


def test_llm_failure_falls_back_to_deterministic_synthesis() -> None:
    pipeline, audit = _pipeline(FakeSynthesisLLM(pick=None))
    record = _run(pipeline, "C-0001")
    assert record.case.status == CaseStatus.COMPLIANT
    synth = [e for e in audit.list_for_case(record.case.case_id) if e.action == "synthesize_strategy"]
    assert synth[0].details is not None and synth[0].details.startswith("[deterministic]")


def test_terminal_status_is_only_persisted_after_the_graph_finishes() -> None:
    # SSE `done` fires on the first terminal status it reads, so the narrate node
    # must not run after a terminal status has already been saved.
    pipeline, _ = _pipeline(None)
    saved: list[CaseStatus] = []
    original_save = pipeline.case_repository.save

    def recording_save(record):  # type: ignore[no-untyped-def]
        saved.append(record.case.status)
        return original_save(record)

    pipeline.case_repository.save = recording_save  # type: ignore[method-assign]
    for client_id, final in (("C-0001", CaseStatus.COMPLIANT), ("C-0004", CaseStatus.REQUIRES_HUMAN_REVIEW)):
        saved.clear()
        _run(pipeline, client_id)
        assert saved[-1] == final
        assert not any(s in {CaseStatus.COMPLIANT, CaseStatus.WARNING, CaseStatus.REQUIRES_HUMAN_REVIEW}
                       for s in saved[:-1]), saved


def test_symbolic_prescreen_excludes_ineligible_products() -> None:
    young = CLIENTS["C-0001"]  # 34, no TTR intent
    types = {p.product_type for p in eligible_products(young, list(SEED_PRODUCTS))}
    assert ProductType.TTR not in types and ProductType.DEFINED_BENEFIT not in types


def test_start_endpoint_runs_in_background_and_stream_ends_with_done() -> None:
    started = api.post("/api/advisory/start", json={"client_id": "C-0004"})
    assert started.status_code == 202
    case_id = started.json()["case_id"]
    assert started.json()["status"] in ("IN_PROGRESS", "REQUIRES_HUMAN_REVIEW")

    with api.stream("GET", f"/api/advisory/{case_id}/stream") as response:
        body = "".join(response.iter_text())
    data_lines = [line for line in body.splitlines() if line.startswith("data: ")]
    assert "event: done" in body
    audit = api.get(f"/api/audit/{case_id}").json()
    assert len(data_lines) - 1 == len(audit)
    assert api.get(f"/api/advisory/{case_id}").json()["status"] == "REQUIRES_HUMAN_REVIEW"
    assert api.get(f"/api/advisory/{case_id}/retrieval").status_code == 200
    detail = api.get(f"/api/advisory/{case_id}/detail").json()
    assert detail["current_step"] == "escalated"
