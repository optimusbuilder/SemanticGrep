from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, Field


class IndexRequest(BaseModel):
    github_url: AnyHttpUrl = Field(
        description="Public GitHub repository URL to clone and index."
    )


class IndexResponse(BaseModel):
    status: Literal["ready"]
    repository: str
    files: int
    chunks: int
    embedding_time_seconds: float


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2_000)
    language: str | None = Field(default=None, max_length=64)


class SearchResult(BaseModel):
    file: str
    start_line: int
    end_line: int
    snippet: str
    embedding_score: float
    rerank_score: float
    language: str


class SearchResponse(BaseModel):
    query: str
    search_time_ms: int
    results: list[SearchResult]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
