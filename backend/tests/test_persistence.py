from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.db.session import create_db_engine, init_db
from app.domain.advisory import AdvisoryCase, AdvisoryCaseRecord, CaseStatus
from app.domain.audit import AuditEvent
from app.repositories.sql import SqlAuditRepository, SqlCaseRepository


@pytest.fixture()
def session_factory(tmp_path):  # type: ignore[no-untyped-def]
    engine = create_db_engine(f"sqlite:///{tmp_path.as_posix()}/t.db")
    yield init_db(engine)
    engine.dispose()


def _event(event_id: str, case_id: str) -> AuditEvent:
    return AuditEvent(event_id=event_id, timestamp=datetime.now(UTC), session_id="s", case_id=case_id,
                      agent="test", action="test", status="success")


def test_audit_table_rejects_update_and_delete(session_factory) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAuditRepository(session_factory)
    repo.append(_event("e1", "CASE-A"))
    repo.append(_event("e2", "CASE-B"))
    assert [e.event_id for e in repo.list_for_case("CASE-A")] == ["e1"]

    for statement in ("UPDATE audit_events SET case_id = 'X'", "DELETE FROM audit_events"):
        with pytest.raises(DBAPIError, match="append-only"), session_factory.begin() as session:
            session.execute(text(statement))
    assert len(repo.list_all()) == 2


def test_case_repository_round_trip_and_upsert(session_factory) -> None:  # type: ignore[no-untyped-def]
    repo = SqlCaseRepository(session_factory)
    now = datetime.now(UTC)
    record = AdvisoryCaseRecord(case=AdvisoryCase(
        case_id="CASE-1", client_id="C-0001", status=CaseStatus.IN_PROGRESS, created_at=now, updated_at=now,
    ))
    repo.save(record)
    repo.save(record.model_copy(update={"case": record.case.model_copy(update={"status": CaseStatus.COMPLIANT})}))
    stored = repo.get("CASE-1")
    assert stored is not None and stored.case.status == CaseStatus.COMPLIANT
    assert len(repo.list()) == 1
