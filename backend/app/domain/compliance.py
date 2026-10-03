from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class ComplianceStatus(str, Enum):
    COMPLIANT = "COMPLIANT"
    WARNING = "WARNING"
    REQUIRES_HUMAN_REVIEW = "REQUIRES_HUMAN_REVIEW"
    REJECTED = "REJECTED"


class ComplianceRuleResult(BaseModel):
    rule_id: str
    category: str
    passed: bool
    is_warning: bool = False
    detail: str
    evidence: str | None = None


class ComplianceResult(BaseModel):
    case_id: str
    status: ComplianceStatus
    rules_evaluated: int
    rules_passed: int
    rules_failed: int
    warnings: int
    rule_results: list[ComplianceRuleResult]
    mandatory_disclosures: list[str]
    engine_version: str
    validated_at: datetime
