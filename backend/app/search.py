import json
import time
from dataclasses import dataclass

from app.config import Settings
from app.models import RetrievedChunk
from app.providers import CohereAnswerer, CohereEmbedder, CohereReranker, PineconeStore


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
class AnswerCitation:
    file: str
    start_line: int
    end_line: int


@dataclass(frozen=True)
class AnswerEvidence:
    file: str
    start_line: int
    end_line: int
    snippet: str
    language: str


@dataclass(frozen=True)
class SearchSummary:
    query: str
    search_time_ms: int
    pinecone_latency_ms: int
    rerank_latency_ms: int
    answer_latency_ms: int
    answer: str | None
    citations: list[AnswerCitation]
    evidence: list[AnswerEvidence]
    results: list[RankedSearchResult]
    vector_results: list[RankedSearchResult]


class RepositorySearcher:
    def __init__(
        self,
        settings: Settings,
        embedder: CohereEmbedder | None = None,
        store: PineconeStore | None = None,
        reranker: CohereReranker | None = None,
        answerer: CohereAnswerer | None = None,
    ) -> None:
        self.embedder = embedder or CohereEmbedder(
            settings.cohere_api_key,
            settings.cohere_tokens_per_minute,
        )
        self.store = store or PineconeStore(settings)
        self.reranker = reranker or CohereReranker(settings.cohere_api_key)
        self.answerer = answerer or CohereAnswerer(
            settings.cohere_api_key,
            settings.cohere_generation_model,
        )

    def search(
        self,
        query: str,
        repository: str,
        language: str | None = None,
        generate_answer: bool = True,
    ) -> SearchSummary:
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
                answer_latency_ms=0,
                answer=None,
                citations=[],
                evidence=[],
                results=[],
                vector_results=[],
            )

        rerank_started_at = time.perf_counter()
        rankings = self.reranker.rerank(query, [candidate.content for candidate in candidates])
        rerank_latency_ms = _elapsed_ms(rerank_started_at)
        results = [_ranked_result(candidates[index], score) for index, score in rankings]
        answer, evidence, answer_latency_ms = (
            self._answer(query, results) if generate_answer else (None, [], 0)
        )
        return SearchSummary(
            query=query,
            search_time_ms=_elapsed_ms(started_at),
            pinecone_latency_ms=pinecone_latency_ms,
            rerank_latency_ms=rerank_latency_ms,
            answer_latency_ms=answer_latency_ms,
            answer=answer,
            citations=[
                AnswerCitation(item.file, item.start_line, item.end_line) for item in evidence
            ],
            evidence=evidence,
            results=results,
            vector_results=[_ranked_result(candidate) for candidate in candidates],
        )

    def _answer(
        self, query: str, results: list[RankedSearchResult]
    ) -> tuple[str | None, list[AnswerEvidence], int]:
        documents = [
            f"Source ID: {index}\n"
            f"File: {result.file}\n"
            f"Lines: {result.start_line}-{result.end_line}\n"
            f"```\n{result.snippet}\n```"
            for index, result in enumerate(results, start=1)
        ]
        started_at = time.perf_counter()
        try:
            response = self.answerer.answer(query, documents)
        except Exception:
            # Search remains useful if the optional explanation stage is unavailable.
            return None, [], 0

        try:
            answer, source_ids = _parse_generated_answer(response, len(results))
        except (json.JSONDecodeError, ValueError):
            # Preserve a usable explanation if the model ignores the requested JSON shape.
            answer = response.strip()
            source_ids = list(range(1, min(3, len(results)) + 1))

        if not answer:
            return None, [], 0
        evidence = [
            AnswerEvidence(
                file=results[source_id - 1].file,
                start_line=results[source_id - 1].start_line,
                end_line=results[source_id - 1].end_line,
                snippet=results[source_id - 1].snippet,
                language=results[source_id - 1].language,
            )
            for source_id in source_ids
        ]
        return answer, evidence, _elapsed_ms(started_at)


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


def _parse_generated_answer(response: str, result_count: int) -> tuple[str, list[int]]:
    content = response.strip()
    if content.startswith("```") and content.endswith("```"):
        content = content[3:-3].removeprefix("json").strip()
    payload = json.loads(content)
    answer = payload.get("answer")
    source_ids = payload.get("source_ids")
    if not isinstance(answer, str) or not answer.strip() or not isinstance(source_ids, list):
        raise ValueError("Generated answer did not match the expected format.")

    selected: list[int] = []
    for source_id in source_ids:
        if not isinstance(source_id, int) or source_id < 1 or source_id > result_count:
            raise ValueError("Generated answer selected an invalid source.")
        if source_id not in selected:
            selected.append(source_id)

    if not selected or len(selected) > 3:
        raise ValueError("Generated answer must select between one and three sources.")
    return answer.strip(), selected
