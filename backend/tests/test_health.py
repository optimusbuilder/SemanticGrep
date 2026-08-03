from fastapi.testclient import TestClient

from app.main import app, jobs


def test_health_returns_service_status() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "reporanker-api"}


def test_search_contract_is_reserved() -> None:
    response = TestClient(app).post("/api/search", json={"query": "Find screenshots"})

    assert response.status_code == 501


def test_index_job_can_be_created_and_polled(monkeypatch) -> None:
    monkeypatch.setattr(jobs, "run", lambda job_id: None)
    client = TestClient(app)

    created = client.post(
        "/api/index",
        json={"github_url": "https://github.com/browserbase/stagehand"},
    )

    assert created.status_code == 202
    assert created.json()["status"] == "queued"
    assert created.json()["mode"] == "fast"

    status = client.get(f"/api/index/{created.json()['id']}")

    assert status.status_code == 200
    assert status.json()["status"] == "queued"
