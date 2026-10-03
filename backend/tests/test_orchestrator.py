from app.domain.advisory import CaseStatus
from app.graph.orchestrator import MAX_ITERATIONS, run_advisory_case
from app.mock_data.clients import SEED_CLIENTS
from app.mock_data.products import SEED_PRODUCTS
from app.repositories.audit_repository import InMemoryAuditRepository
from app.repositories.document_repository import InMemoryDocumentRepository
from app.services.advisory_service import MockAdvisoryService
from app.services.compliance_service import ComplianceService
from app.services.retrieval_service import MockRetrievalService

CLIENTS_BY_ID = {c.client_id: c for c in SEED_CLIENTS}


def _run(client_id: str):
    audit_repository = InMemoryAuditRepository()
    document_repository = InMemoryDocumentRepository([])
    return run_advisory_case(
        profile=CLIENTS_BY_ID[client_id],
        products=list(SEED_PRODUCTS),
        retrieval_service=MockRetrievalService(document_repository),
        advisory_service=MockAdvisoryService(),
        compliance_service=ComplianceService(),
        audit_repository=audit_repository,
        session_id="test-session",
    ), audit_repository


def test_self_correction_scenario_resolves_to_compliant() -> None:
    result, _ = _run("C-0002")
    assert result.case.status == CaseStatus.COMPLIANT
    assert result.case.iteration_count == 2
    assert any("allocation" in note.lower() or "growth" in note.lower() for note in result.critique_notes)


def test_unfixable_breach_escalates_to_human_review() -> None:
    result, audit_repository = _run("C-0004")
    assert result.case.status == CaseStatus.REQUIRES_HUMAN_REVIEW
    assert result.case.iteration_count == MAX_ITERATIONS
    assert len(result.compliance_history) == MAX_ITERATIONS

    events = audit_repository.list_for_case(result.case.case_id)
    assert any(e.action == "max_iterations_reached" for e in events)


def test_clean_scenario_passes_first_iteration() -> None:
    result, _ = _run("C-0001")
    assert result.case.status == CaseStatus.COMPLIANT
    assert result.case.iteration_count == 1


def test_warning_scenario_does_not_retry() -> None:
    result, _ = _run("C-0006")
    assert result.case.status == CaseStatus.WARNING
    assert result.case.iteration_count == 1
