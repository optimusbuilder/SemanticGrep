from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.schemas import (
    HealthResponse,
    IndexRequest,
    IndexResponse,
    SearchRequest,
    SearchResponse,
)

settings = get_settings()

app = FastAPI(
    title="RepoRanker API",
    version="0.1.0",
    description="An end-to-end source-code retrieval pipeline.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="reporanker-api")


@app.post("/api/index", response_model=IndexResponse, status_code=501)
def index_repository(request: IndexRequest) -> IndexResponse:
    """Reserve the ingestion API contract before pipeline wiring is added."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Indexing is not implemented for {request.github_url}.",
    )


@app.post("/api/search", response_model=SearchResponse, status_code=501)
def search_repository(request: SearchRequest) -> SearchResponse:
    """Reserve the retrieval API contract before provider wiring is added."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Search is not implemented for query {request.query!r}.",
    )
