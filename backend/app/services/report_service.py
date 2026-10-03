from datetime import UTC, datetime

from pydantic import BaseModel

from app.domain.advisory import AdvisoryCase
from app.domain.client import ClientProfile
from app.domain.compliance import ComplianceResult


class StatementOfAdvice(BaseModel):
    case_id: str
    client_id: str
    generated_at: datetime
    executive_summary: str
    client_profile: ClientProfile
    objectives: list[str]
    recommended_strategy: dict
    compliance_verification: ComplianceResult
    disclosures: list[str]
    is_demo_data: bool = True


class ReportService:
    def generate(
        self, case: AdvisoryCase, profile: ClientProfile, compliance: ComplianceResult
    ) -> StatementOfAdvice:
        recommendation = case.recommendation
        return StatementOfAdvice(
            case_id=case.case_id,
            client_id=case.client_id,
            generated_at=datetime.now(UTC),
            executive_summary=(
                f"This Statement of Advice outlines a recommended superannuation strategy for "
                f"{profile.full_name}, validated against deterministic Australian superannuation "
                f"compliance rules (engine {compliance.engine_version})."
            ),
            client_profile=profile,
            objectives=profile.financial_goals or ["Not specified"],
            recommended_strategy=recommendation.model_dump() if recommendation else {},
            compliance_verification=compliance,
            disclosures=recommendation.disclosures if recommendation else [],
        )
