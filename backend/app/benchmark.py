from dataclasses import dataclass

from app.search import RepositorySearcher


@dataclass(frozen=True)
class BenchmarkCase:
    query: str
    expected_file: str


STAGEHAND_CASES = [
    BenchmarkCase(
        query="How does agent replay recording work?",
        expected_file="packages/core/lib/v3/cache/AgentCache.ts",
    ),
    BenchmarkCase(
        query="Where are screenshots captured after agent actions?",
        expected_file="packages/core/lib/v3/agent/utils/screenshotHandler.ts",
    ),
    BenchmarkCase(
        query="How are computer-use actions handled?",
        expected_file="packages/core/lib/v3/handlers/v3CuaAgentHandler.ts",
    ),
    BenchmarkCase(
        query="Where is the agent screenshot tool implemented?",
        expected_file="packages/core/lib/v3/agent/tools/screenshot.ts",
    ),
    BenchmarkCase(
        query="How does a page capture a screenshot?",
        expected_file="packages/core/lib/v3/understudy/page.ts",
    ),
]


@dataclass(frozen=True)
class BenchmarkCaseResult:
    query: str
    expected_file: str
    vector_rank: int | None
    rerank_rank: int | None


@dataclass(frozen=True)
class BenchmarkSummary:
    repository: str
    vector_recall_at_5: float
    rerank_recall_at_5: float
    vector_mrr: float
    rerank_mrr: float
    cases: list[BenchmarkCaseResult]


def run_stagehand_benchmark(searcher: RepositorySearcher, repository: str) -> BenchmarkSummary:
    cases = []
    for case in STAGEHAND_CASES:
        summary = searcher.search(case.query, repository, "typescript", generate_answer=False)
        vector_files = [result.file for result in summary.vector_results]
        reranked_files = [result.file for result in summary.results]
        cases.append(
            BenchmarkCaseResult(
                query=case.query,
                expected_file=case.expected_file,
                vector_rank=_rank(case.expected_file, vector_files),
                rerank_rank=_rank(case.expected_file, reranked_files),
            )
        )
    return BenchmarkSummary(
        repository=repository,
        vector_recall_at_5=_recall_at_5([case.vector_rank for case in cases]),
        rerank_recall_at_5=_recall_at_5([case.rerank_rank for case in cases]),
        vector_mrr=_mrr([case.vector_rank for case in cases]),
        rerank_mrr=_mrr([case.rerank_rank for case in cases]),
        cases=cases,
    )


def _rank(expected_file: str, files: list[str]) -> int | None:
    try:
        return files.index(expected_file) + 1
    except ValueError:
        return None


def _recall_at_5(ranks: list[int | None]) -> float:
    return round(sum(rank is not None and rank <= 5 for rank in ranks) / len(ranks) * 100, 1)


def _mrr(ranks: list[int | None]) -> float:
    return round(sum(1 / rank if rank is not None else 0 for rank in ranks) / len(ranks), 3)
