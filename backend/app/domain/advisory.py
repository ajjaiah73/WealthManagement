from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.domain.compliance import ComplianceResult
from app.domain.retrieval import RetrievedDocument


class CaseStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLIANT = "COMPLIANT"
    WARNING = "WARNING"
    REQUIRES_HUMAN_REVIEW = "REQUIRES_HUMAN_REVIEW"
    REJECTED = "REJECTED"


class AdvisoryRecommendation(BaseModel):
    strategy_name: str
    product_id: str
    product_type: str
    allocation: str
    fee_percentage: float
    rationale: str
    assumptions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    source_documents: list[str] = Field(default_factory=list)
    disclosures: list[str] = Field(default_factory=list)


class AdvisoryCase(BaseModel):
    case_id: str
    client_id: str
    status: CaseStatus
    iteration_count: int = 0
    recommendation: AdvisoryRecommendation | None = None
    created_at: datetime
    updated_at: datetime


class AdvisoryCaseRecord(BaseModel):
    """Full server-side record for a case — the AdvisoryCase plus everything
    needed to answer the compliance/audit/report endpoints without recomputation."""

    case: AdvisoryCase
    compliance_history: list[ComplianceResult] = Field(default_factory=list)
    critique_notes: list[str] = Field(default_factory=list)
    retrieved_documents: list[RetrievedDocument] = Field(default_factory=list)
    request: str | None = None
    goal: str | None = None
    constraints: list[str] = Field(default_factory=list)
    retrieval_query: str | None = None
    graph_context: list[str] = Field(default_factory=list)
    current_step: str | None = None
