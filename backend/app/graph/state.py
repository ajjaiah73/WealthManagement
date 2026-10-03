"""AdvisoryState — the strongly-typed shared state threaded through the
LangGraph StateGraph in app.graph.orchestrator. Each node reads this model
and returns a partial update; LangGraph merges updates between supersteps.
"""
from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.advisory import AdvisoryRecommendation, CaseStatus
from app.domain.client import ClientProfile
from app.domain.compliance import ComplianceResult
from app.domain.retrieval import RetrievedDocument


class UserIntent(BaseModel):
    raw_request: str
    goal: str | None = None
    constraints: list[str] = Field(default_factory=list)
    retrieval_query: str | None = None
    method: str | None = None  # "llm" | "deterministic"


class ExecutionMetadata(BaseModel):
    session_id: str
    case_id: str
    started_at: datetime
    updated_at: datetime
    model: str | None = None
    model_version: str | None = None


class AdvisoryState(BaseModel):
    client_profile: ClientProfile
    user_intent: UserIntent
    retrieved_documents: list[RetrievedDocument] = Field(default_factory=list)
    graph_context: list[str] = Field(default_factory=list)
    market_context: list[str] = Field(default_factory=list)
    candidate_strategies: list[AdvisoryRecommendation] = Field(default_factory=list)
    selected_strategy: AdvisoryRecommendation | None = None
    compliance_results: list[ComplianceResult] = Field(default_factory=list)
    critique_notes: list[str] = Field(default_factory=list)
    audit_events: list[str] = Field(default_factory=list)  # event IDs; full events live in the audit repository
    iteration_count: int = 0
    final_advice: AdvisoryRecommendation | None = None
    status: CaseStatus = CaseStatus.IN_PROGRESS
    current_step: str | None = None
    execution_metadata: ExecutionMetadata
