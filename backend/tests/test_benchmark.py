from app.benchmark import STAGEHAND_CASES, run_stagehand_benchmark
from app.search import RankedSearchResult, SearchSummary


class FakeSearcher:
    def search(self, query: str, *_: object, **__: object) -> SearchSummary:
        expected = next(case.expected_file for case in STAGEHAND_CASES if case.query == query)
        result = RankedSearchResult(expected, 1, 10, "code", 0.8, 0.9, "typescript")
        vector_results = [result] if "recording" in query else []
        return SearchSummary(query, 10, 3, 4, 0, None, [], [result], vector_results)


def test_benchmark_compares_vector_and_rerank_top_five() -> None:
    summary = run_stagehand_benchmark(FakeSearcher(), "browserbase/stagehand")  # type: ignore[arg-type]

    assert summary.vector_recall_at_5 == 20.0
    assert summary.rerank_recall_at_5 == 100.0
    assert summary.vector_mrr == 0.2
    assert summary.rerank_mrr == 1.0
