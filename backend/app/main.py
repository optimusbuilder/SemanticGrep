from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.ingestion import RepositoryIndexer
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


@app.post("/api/index", response_model=IndexResponse)
def index_repository(request: IndexRequest) -> IndexResponse:
    try:
        summary = RepositoryIndexer(settings).index(str(request.github_url))
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Repository indexing failed.",
        ) from error
    return IndexResponse(status="ready", **summary.__dict__)


@app.post("/api/search", response_model=SearchResponse, status_code=501)
def search_repository(request: SearchRequest) -> SearchResponse:
    """Reserve the retrieval API contract before provider wiring is added."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Search is not implemented for query {request.query!r}.",
    )
