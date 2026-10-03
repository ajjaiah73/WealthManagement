from fastapi import APIRouter

from app.container import container
from app.domain.audit import AuditEvent

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("", response_model=list[AuditEvent])
def list_all_audit_events() -> list[AuditEvent]:
    return container.audit_repository.list_all()


@router.get("/{case_id}", response_model=list[AuditEvent])
def get_audit_trail(case_id: str) -> list[AuditEvent]:
    return container.audit_repository.list_for_case(case_id)
