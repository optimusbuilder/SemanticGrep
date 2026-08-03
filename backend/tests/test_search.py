from app.config import get_settings
from app.models import RetrievedChunk
from app.search import RepositorySearcher, _parse_generated_answer


class FakeEmbedder:
    def embed_query(self, query: str) -> list[float]:
        assert query == "Where are screenshots captured?"
        return [0.1, 0.2]


class FakeStore:
    def __init__(self) -> None:
        self.request: tuple[list[float], str, str | None] | None = None

    def query_repository(
        self, query_embedding: list[float], repository: str, language: str | None
    ) -> list[RetrievedChunk]:
        self.request = (query_embedding, repository, language)
        return [
            RetrievedChunk(
                file_path="src/browser.ts",
                start_line=10,
                end_line=30,
                language="typescript",
                content="export function launchBrowser() { return chromium.launch(); }",
                embedding_score=0.82,
            ),
            RetrievedChunk(
                file_path="src/screenshot.ts",
                start_line=40,
                end_line=62,
                language="typescript",
                content="export async function screenshot() { return page.screenshot(); }",
                embedding_score=0.77,
            ),
        ]


class FakeReranker:
    def rerank(self, query: str, documents: list[str]) -> list[tuple[int, float]]:
        assert query == "Where are screenshots captured?"
        assert len(documents) == 2
        return [(1, 0.98), (0, 0.42)]


class FakeAnswerer:
    def answer(self, query: str, documents: list[str]) -> str:
        assert query == "Where are screenshots captured?"
        assert "Source ID: 1" in documents[0]
        assert "src/screenshot.ts" in documents[0]
        return (
            '{"answer":"Screenshots are captured by `page.screenshot()` '
            'in the screenshot handler.",'
            '"source_ids":[1]}'
        )


def test_search_reranks_pinecone_candidates_and_preserves_both_scores() -> None:
    store = FakeStore()
    searcher = RepositorySearcher(
        get_settings(),
        embedder=FakeEmbedder(),  # type: ignore[arg-type]
        store=store,  # type: ignore[arg-type]
        reranker=FakeReranker(),  # type: ignore[arg-type]
        answerer=FakeAnswerer(),  # type: ignore[arg-type]
    )

    summary = searcher.search(
        "Where are screenshots captured?", "browserbase/stagehand", "typescript"
    )

    assert store.request == ([0.1, 0.2], "browserbase/stagehand", "typescript")
    result_scores = [
        (result.file, result.embedding_score, result.rerank_score) for result in summary.results
    ]
    assert result_scores == [
        ("src/screenshot.ts", 0.77, 0.98),
        ("src/browser.ts", 0.82, 0.42),
    ]
    assert [result.file for result in summary.vector_results] == [
        "src/browser.ts",
        "src/screenshot.ts",
    ]
    assert summary.answer == (
        "Screenshots are captured by `page.screenshot()` in the screenshot handler."
    )
    assert [(citation.file, citation.start_line) for citation in summary.citations] == [
        ("src/screenshot.ts", 40),
    ]
    assert [(item.file, item.snippet) for item in summary.evidence] == [
        ("src/screenshot.ts", "export async function screenshot() { return page.screenshot(); }")
    ]


def test_search_skips_rerank_when_vector_search_returns_no_candidates() -> None:
    class EmptyStore:
        def query_repository(self, *_: object) -> list[RetrievedChunk]:
            return []

    class FailingReranker:
        def rerank(self, *_: object) -> list[tuple[int, float]]:
            raise AssertionError("Rerank should not run without vector candidates")

    searcher = RepositorySearcher(
        get_settings(),
        embedder=FakeEmbedder(),  # type: ignore[arg-type]
        store=EmptyStore(),  # type: ignore[arg-type]
        reranker=FailingReranker(),  # type: ignore[arg-type]
        answerer=FakeAnswerer(),  # type: ignore[arg-type]
    )

    summary = searcher.search("Where are screenshots captured?", "browserbase/stagehand")

    assert summary.results == []
    assert summary.vector_results == []
    assert summary.rerank_latency_ms == 0


def test_generated_answer_accepts_json_in_a_markdown_fence() -> None:
    answer, source_ids = _parse_generated_answer(
        '```json\n{"answer":"Uses the screenshot handler.","source_ids":[2]}\n```', 2
    )

    assert answer == "Uses the screenshot handler."
    assert source_ids == [2]


def test_search_preserves_plain_text_answers_when_source_selection_is_invalid() -> None:
    class PlainTextAnswerer:
        def answer(self, *_: object) -> str:
            return "Screenshots are captured through the configured provider."

    searcher = RepositorySearcher(
        get_settings(),
        embedder=FakeEmbedder(),  # type: ignore[arg-type]
        store=FakeStore(),  # type: ignore[arg-type]
        reranker=FakeReranker(),  # type: ignore[arg-type]
        answerer=PlainTextAnswerer(),  # type: ignore[arg-type]
    )

    summary = searcher.search("Where are screenshots captured?", "browserbase/stagehand")

    assert summary.answer == "Screenshots are captured through the configured provider."
    assert [item.file for item in summary.evidence] == [
        "src/screenshot.ts",
        "src/browser.ts",
    ]
