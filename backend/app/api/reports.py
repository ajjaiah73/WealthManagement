from fastapi import APIRouter, HTTPException

from app.container import container
from app.services.report_service import StatementOfAdvice

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("/{case_id}/generate", response_model=StatementOfAdvice)
def generate_report(case_id: str) -> StatementOfAdvice:
    record = container.case_repository.get(case_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Advisory case not found")
    client = container.client_repository.get(record.case.client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    if not record.compliance_history:
        raise HTTPException(status_code=409, detail="Case has no compliance result yet")
    return container.report_service.generate(record.case, client, record.compliance_history[-1])
