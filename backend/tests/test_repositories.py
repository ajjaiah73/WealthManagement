from app.domain.audit import AuditEvent
from app.domain.client import ClientProfile
from app.repositories.audit_repository import InMemoryAuditRepository
from app.repositories.client_repository import InMemoryClientRepository


def test_client_repository_get_list_add_update() -> None:
    repo = InMemoryClientRepository([])
    client = ClientProfile(client_id="C-1", first_name="A", last_name="B")
    repo.add(client)

    assert repo.get("C-1") == client
    assert repo.list() == [client]

    updated = client.model_copy(update={"age": 50})
    repo.update(updated)
    assert repo.get("C-1").age == 50  # type: ignore[union-attr]


def test_audit_repository_is_append_only_and_filters_by_case() -> None:
    repo = InMemoryAuditRepository()
    event_a = AuditEvent(event_id="1", timestamp="2026-01-01T00:00:00Z", session_id="s1", case_id="CASE-A",
                         agent="test", action="test", status="success")
    event_b = AuditEvent(event_id="2", timestamp="2026-01-01T00:00:00Z", session_id="s1", case_id="CASE-B",
                         agent="test", action="test", status="success")
    repo.append(event_a)
    repo.append(event_b)

    assert repo.list_for_case("CASE-A") == [event_a]
    assert len(repo.list_all()) == 2
