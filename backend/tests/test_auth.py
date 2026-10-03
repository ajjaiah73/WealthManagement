import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _auth_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "auth_enabled", True)


def _token(username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    return body["access_token"]


def test_protected_endpoints_require_token() -> None:
    assert client.get("/api/clients").status_code == 401
    assert client.get("/api/advisory").status_code == 401
    assert client.get("/api/clients", headers={"Authorization": "Bearer not-a-jwt"}).status_code == 401


def test_health_and_login_are_public() -> None:
    assert client.get("/api/health").status_code == 200
    assert client.post("/api/auth/login", json={"username": "advisor", "password": "wrong"}).status_code == 401
    assert client.post("/api/auth/login", json={"username": "nobody", "password": "x"}).status_code == 401


def test_advisor_can_read_and_run() -> None:
    headers = {"Authorization": f"Bearer {_token('advisor', 'advisor-demo')}"}
    me = client.get("/api/auth/me", headers=headers).json()
    assert me == {"user_id": "advisor", "display_name": "Demo Advisor", "role": "advisor"}
    assert client.get("/api/clients", headers=headers).status_code == 200
    run = client.post("/api/advisory/run", json={"client_id": "C-0001"}, headers=headers)
    assert run.status_code == 201


def test_compliance_officer_is_read_only() -> None:
    headers = {"Authorization": f"Bearer {_token('compliance', 'compliance-demo')}"}
    assert client.get("/api/clients", headers=headers).status_code == 200
    assert client.get("/api/audit", headers=headers).status_code == 200
    assert client.post("/api/advisory/run", json={"client_id": "C-0001"}, headers=headers).status_code == 403
    fact_find = client.post("/api/fact-find", json={"client_id": "C-0001", "updates": {}}, headers=headers)
    assert fact_find.status_code == 403


def test_token_accepted_as_query_parameter_for_sse() -> None:
    token = _token("admin", "admin-demo")
    assert client.get(f"/api/advisory?access_token={token}").status_code == 200
