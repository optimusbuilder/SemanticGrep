from fastapi.testclient import TestClient

import app.main as main
from app.main import app, jobs
from app.search import AnswerCitation, RankedSearchResult, SearchSummary


def test_health_returns_service_status() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "reporanker-api"}


def test_search_requires_repository_scope() -> None:
    response = TestClient(app).post("/api/search", json={"query": "Find screenshots"})

    assert response.status_code == 422


def test_search_response_serializes_ranked_results(monkeypatch) -> None:
    result = RankedSearchResult(
        file="src/screenshot.ts",
        start_line=40,
        end_line=62,
        snippet="return page.screenshot();",
        embedding_score=0.77,
        rerank_score=0.98,
        language="typescript",
    )

    class FakeSearcher:
        def __init__(self, *_: object) -> None:
            pass

        def search(self, *_: object) -> SearchSummary:
            return SearchSummary(
                query="Where are screenshots captured?",
                search_time_ms=100,
                pinecone_latency_ms=30,
                rerank_latency_ms=50,
                answer_latency_ms=70,
                answer="Screenshots are captured in screenshot.ts.",
                citations=[AnswerCitation("src/screenshot.ts", 40, 62)],
                results=[result],
                vector_results=[result],
            )

    monkeypatch.setattr(main, "RepositorySearcher", FakeSearcher)

    response = TestClient(app).post(
        "/api/search",
        json={
            "query": "Where are screenshots captured?",
            "repository": "browserbase/stagehand",
        },
    )

    assert response.status_code == 200
    assert response.json()["results"][0]["rerank_score"] == 0.98
    assert response.json()["citations"][0]["file"] == "src/screenshot.ts"


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


def test_repository_catalog_lists_indexed_namespaces(monkeypatch) -> None:
    class FakeStore:
        def __init__(self, *_: object) -> None:
            pass

        def list_repositories(self) -> list[tuple[str, int]]:
            return [("browserbase/stagehand", 2_000), ("optimusbuilder/contractbot", 381)]

    monkeypatch.setattr(main, "PineconeStore", FakeStore)

    response = TestClient(app).get("/api/repositories")

    assert response.status_code == 200
    assert response.json()["repositories"][0] == {
        "repository": "browserbase/stagehand",
        "chunks": 2000,
    }
