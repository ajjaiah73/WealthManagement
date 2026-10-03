from app.domain.audit import AuditEvent


class InMemoryAuditRepository:
    """Append-only from the application's perspective — no update/delete methods
    are exposed. Real deployments would back this with an insert-only Postgres
    table (or similar) with no UPDATE/DELETE grants."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> AuditEvent:
        self._events.append(event)
        return event

    def list_for_case(self, case_id: str) -> list[AuditEvent]:
        return [e for e in self._events if e.case_id == case_id]

    def list_all(self) -> list[AuditEvent]:
        return list(self._events)
