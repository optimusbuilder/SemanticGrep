from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_service_status() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "reporanker-api"}


def test_search_contract_is_reserved() -> None:
    response = TestClient(app).post("/api/search", json={"query": "Find screenshots"})

    assert response.status_code == 501
