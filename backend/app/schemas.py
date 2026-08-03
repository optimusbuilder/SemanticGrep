from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, Field, field_validator


class IndexRequest(BaseModel):
    github_url: AnyHttpUrl = Field(
        description="Public GitHub repository URL to clone and index."
    )
    mode: Literal["fast", "full"] = "fast"
    max_chunks: int | None = Field(default=None, ge=1, le=20_000)

    @field_validator("github_url")
    @classmethod
    def require_public_github_repository(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        path_parts = [part for part in value.path.split("/") if part]
        if value.host != "github.com" or len(path_parts) != 2:
            raise ValueError("github_url must be a public https://github.com/owner/repository URL")
        return value


class IndexJobResponse(BaseModel):
    id: str
    status: Literal[
        "queued", "cloning", "filtering", "chunking", "embedding", "upserting", "ready", "failed"
    ]
    repository: str
    mode: Literal["fast", "full"]
    progress: int
    files: int | None = None
    chunks: int | None = None
    available_chunks: int | None = None
    skipped_chunks: int | None = None
    embedding_time_seconds: float | None = None
    error: str | None = None


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2_000)
    repository: str = Field(pattern=r"^[\w.-]+/[\w.-]+$")
    language: str | None = Field(default=None, max_length=64)


class SearchResult(BaseModel):
    file: str
    start_line: int
    end_line: int
    snippet: str
    embedding_score: float
    rerank_score: float | None
    language: str


class AnswerCitation(BaseModel):
    file: str
    start_line: int
    end_line: int


class AnswerEvidence(BaseModel):
    file: str
    start_line: int
    end_line: int
    snippet: str
    language: str


class SearchResponse(BaseModel):
    query: str
    search_time_ms: int
    pinecone_latency_ms: int
    rerank_latency_ms: int
    answer_latency_ms: int
    answer: str | None
    citations: list[AnswerCitation]
    evidence: list[AnswerEvidence]
    results: list[SearchResult]
    vector_results: list[SearchResult]


class BenchmarkRequest(BaseModel):
    repository: str = Field(pattern=r"^[\w.-]+/[\w.-]+$")


class BenchmarkCaseResponse(BaseModel):
    query: str
    expected_file: str
    vector_rank: int | None
    rerank_rank: int | None


class BenchmarkResponse(BaseModel):
    repository: str
    vector_recall_at_5: float
    rerank_recall_at_5: float
    vector_mrr: float
    rerank_mrr: float
    cases: list[BenchmarkCaseResponse]


class RepositorySummary(BaseModel):
    repository: str
    chunks: int


class RepositoryListResponse(BaseModel):
    repositories: list[RepositorySummary]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
