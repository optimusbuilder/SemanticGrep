import time
from dataclasses import dataclass

from app.config import Settings
from app.models import RetrievedChunk
from app.providers import CohereEmbedder, CohereReranker, PineconeStore


@dataclass(frozen=True)
class RankedSearchResult:
    file: str
    start_line: int
    end_line: int
    snippet: str
    embedding_score: float
    rerank_score: float | None
    language: str


@dataclass(frozen=True)
class SearchSummary:
    query: str
    search_time_ms: int
    pinecone_latency_ms: int
    rerank_latency_ms: int
    results: list[RankedSearchResult]
    vector_results: list[RankedSearchResult]


class RepositorySearcher:
    def __init__(
        self,
        settings: Settings,
        embedder: CohereEmbedder | None = None,
        store: PineconeStore | None = None,
        reranker: CohereReranker | None = None,
    ) -> None:
        self.embedder = embedder or CohereEmbedder(
            settings.cohere_api_key,
            settings.cohere_tokens_per_minute,
        )
        self.store = store or PineconeStore(settings)
        self.reranker = reranker or CohereReranker(settings.cohere_api_key)

    def search(self, query: str, repository: str, language: str | None = None) -> SearchSummary:
        started_at = time.perf_counter()
        query_embedding = self.embedder.embed_query(query)

        pinecone_started_at = time.perf_counter()
        candidates = self.store.query_repository(query_embedding, repository, language)
        pinecone_latency_ms = _elapsed_ms(pinecone_started_at)
        if not candidates:
            return SearchSummary(
                query=query,
                search_time_ms=_elapsed_ms(started_at),
                pinecone_latency_ms=pinecone_latency_ms,
                rerank_latency_ms=0,
                results=[],
                vector_results=[],
            )

        rerank_started_at = time.perf_counter()
        rankings = self.reranker.rerank(query, [candidate.content for candidate in candidates])
        rerank_latency_ms = _elapsed_ms(rerank_started_at)
        results = [_ranked_result(candidates[index], score) for index, score in rankings]
        return SearchSummary(
            query=query,
            search_time_ms=_elapsed_ms(started_at),
            pinecone_latency_ms=pinecone_latency_ms,
            rerank_latency_ms=rerank_latency_ms,
            results=results,
            vector_results=[_ranked_result(candidate) for candidate in candidates],
        )


def _ranked_result(
    candidate: RetrievedChunk, rerank_score: float | None = None
) -> RankedSearchResult:
    return RankedSearchResult(
        file=candidate.file_path,
        start_line=candidate.start_line,
        end_line=candidate.end_line,
        snippet=candidate.content,
        embedding_score=candidate.embedding_score,
        rerank_score=rerank_score,
        language=candidate.language,
    )


def _elapsed_ms(started_at: float) -> int:
    return round((time.perf_counter() - started_at) * 1_000)
