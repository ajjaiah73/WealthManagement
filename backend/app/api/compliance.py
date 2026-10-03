from fastapi import APIRouter, HTTPException

from app.container import container
from app.domain.compliance import ComplianceResult

router = APIRouter(prefix="/api/compliance", tags=["compliance"])


@router.get("/{case_id}", response_model=ComplianceResult)
def get_compliance_result(case_id: str) -> ComplianceResult:
    record = container.case_repository.get(case_id)
    if record is None or not record.compliance_history:
        raise HTTPException(status_code=404, detail="Compliance result not found")
    return record.compliance_history[-1]
