from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["demo_mode"] is True


def test_golden_path_self_correction_scenario() -> None:
    clients = client.get("/api/clients").json()
    assert len(clients) >= 10

    profile = client.get("/api/clients/C-0002")
    assert profile.status_code == 200

    run = client.post("/api/advisory/run", json={"client_id": "C-0002"})
    assert run.status_code == 201
    case = run.json()
    assert case["status"] == "COMPLIANT"
    assert case["iteration_count"] == 2
    case_id = case["case_id"]

    fetched_case = client.get(f"/api/advisory/{case_id}")
    assert fetched_case.status_code == 200

    compliance = client.get(f"/api/compliance/{case_id}")
    assert compliance.status_code == 200
    assert compliance.json()["status"] == "COMPLIANT"

    audit = client.get(f"/api/audit/{case_id}")
    assert audit.status_code == 200
    assert len(audit.json()) > 0

    all_audit = client.get("/api/audit")
    assert all_audit.status_code == 200
    assert len(all_audit.json()) >= len(audit.json())

    all_cases = client.get("/api/advisory")
    assert all_cases.status_code == 200
    assert any(c["case_id"] == case_id for c in all_cases.json())

    report = client.post(f"/api/reports/{case_id}/generate")
    assert report.status_code == 200
    assert report.json()["is_demo_data"] is True


def test_human_review_scenario() -> None:
    run = client.post("/api/advisory/run", json={"client_id": "C-0004"})
    assert run.status_code == 201
    case = run.json()
    assert case["status"] == "REQUIRES_HUMAN_REVIEW"
    assert case["iteration_count"] == 3


def test_products_and_documents_endpoints() -> None:
    products = client.get("/api/products")
    assert products.status_code == 200
    assert len(products.json()) >= 10

    documents = client.get("/api/documents")
    assert documents.status_code == 200
    assert len(documents.json()) >= 20

    document = client.get("/api/documents/DOC-014")
    assert document.status_code == 200
    assert document.json()["document_type"] == "Legislation"

    missing = client.get("/api/documents/DOC-DOES-NOT-EXIST")
    assert missing.status_code == 404


def test_fact_find_surfaces_missing_fields() -> None:
    fact_find = client.get("/api/fact-find/C-0005")
    assert fact_find.status_code == 200
    fields = {f["field"]: f["status"] for f in fact_find.json()["fields"]}
    assert fields["risk_tolerance"] == "missing"
    assert fields["age"] == "present"


def test_fact_find_rejects_invalid_updates_without_corrupting_profile() -> None:
    before = client.get("/api/clients/C-0010").json()
    other = client.get("/api/clients/C-0001").json()

    bad_type = {"client_id": "C-0010", "updates": {"age": "not-a-number"}}
    unknown = {"client_id": "C-0010", "updates": {"hacker_field": 1}}
    rename = {"client_id": "C-0010", "updates": {"client_id": "C-0001"}}
    out_of_range = {"client_id": "C-0010", "updates": {"age": 5}}
    for payload in (bad_type, unknown, rename, out_of_range):
        assert client.post("/api/fact-find", json=payload).status_code == 422

    assert client.get("/api/clients/C-0010").json() == before
    assert client.get("/api/clients/C-0001").json() == other


def test_fact_find_accepts_valid_update() -> None:
    original = client.get("/api/clients/C-0010").json()["target_retirement_age"]
    response = client.post(
        "/api/fact-find", json={"client_id": "C-0010", "updates": {"target_retirement_age": 66}}
    )
    assert response.status_code == 200
    assert client.get("/api/clients/C-0010").json()["target_retirement_age"] == 66
    client.post(
        "/api/fact-find", json={"client_id": "C-0010", "updates": {"target_retirement_age": original}}
    )


def test_unknown_case_returns_404_everywhere() -> None:
    assert client.get("/api/advisory/CASE-NOPE").status_code == 404
    assert client.get("/api/advisory/CASE-NOPE/stream").status_code == 404
    assert client.get("/api/compliance/CASE-NOPE").status_code == 404
    assert client.post("/api/reports/CASE-NOPE/generate").status_code == 404
    assert client.get("/api/audit/CASE-NOPE").json() == []
