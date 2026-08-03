from fastapi import BackgroundTasks, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.jobs import IndexJob, IndexJobManager
from app.schemas import (
    AnswerCitation,
    HealthResponse,
    IndexJobResponse,
    IndexRequest,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from app.search import RepositorySearcher

settings = get_settings()
jobs = IndexJobManager(settings)

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


@app.post("/api/index", response_model=IndexJobResponse, status_code=status.HTTP_202_ACCEPTED)
def index_repository(request: IndexRequest, background_tasks: BackgroundTasks) -> IndexJobResponse:
    max_chunks = request.max_chunks
    if max_chunks is None and request.mode == "fast":
        max_chunks = settings.fast_index_max_chunks
    job = jobs.create(str(request.github_url), request.mode, max_chunks)
    background_tasks.add_task(jobs.run, job.id)
    return _job_response(job)


@app.get("/api/index/{job_id}", response_model=IndexJobResponse)
def index_status(job_id: str) -> IndexJobResponse:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Index job not found.")
    return _job_response(job)


@app.post("/api/search", response_model=SearchResponse)
def search_repository(request: SearchRequest) -> SearchResponse:
    try:
        summary = RepositorySearcher(settings).search(
            request.query,
            request.repository,
            request.language,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Repository search failed.",
        ) from error
    return SearchResponse(
        query=summary.query,
        search_time_ms=summary.search_time_ms,
        pinecone_latency_ms=summary.pinecone_latency_ms,
        rerank_latency_ms=summary.rerank_latency_ms,
        answer_latency_ms=summary.answer_latency_ms,
        answer=summary.answer,
        citations=[AnswerCitation(**citation.__dict__) for citation in summary.citations],
        results=[SearchResult(**result.__dict__) for result in summary.results],
        vector_results=[SearchResult(**result.__dict__) for result in summary.vector_results],
    )


def _job_response(job: IndexJob) -> IndexJobResponse:
    summary = job.summary
    return IndexJobResponse(
        id=job.id,
        status=job.status,
        repository=job.repository,
        mode=job.mode,
        progress=job.progress,
        files=summary.files if summary else None,
        chunks=summary.chunks if summary else None,
        available_chunks=summary.available_chunks if summary else None,
        skipped_chunks=summary.skipped_chunks if summary else None,
        embedding_time_seconds=summary.embedding_time_seconds if summary else None,
        error=job.error,
    )
