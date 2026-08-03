from dataclasses import dataclass
from threading import Lock
from typing import Literal
from uuid import uuid4

from app.config import Settings
from app.ingestion import IndexingSummary, RepositoryIndexer
from app.repository import repository_name

JobStatus = Literal[
    "queued",
    "cloning",
    "filtering",
    "chunking",
    "embedding",
    "upserting",
    "ready",
    "failed",
]


@dataclass
class IndexJob:
    id: str
    github_url: str
    mode: str
    max_chunks: int | None
    repository: str
    status: JobStatus = "queued"
    progress: int = 0
    summary: IndexingSummary | None = None
    error: str | None = None


class IndexJobManager:
    """In-memory job tracking for a single Railway service instance."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.jobs: dict[str, IndexJob] = {}
        self.lock = Lock()

    def create(self, github_url: str, mode: str, max_chunks: int | None) -> IndexJob:
        job = IndexJob(
            id=str(uuid4()),
            github_url=github_url,
            mode=mode,
            max_chunks=max_chunks,
            repository=repository_name(github_url),
        )
        with self.lock:
            self.jobs[job.id] = job
        return job

    def get(self, job_id: str) -> IndexJob | None:
        with self.lock:
            return self.jobs.get(job_id)

    def run(self, job_id: str) -> None:
        job = self.get(job_id)
        if job is None:
            return
        try:
            summary = RepositoryIndexer(self.settings).index(
                job.github_url,
                max_chunks=job.max_chunks,
                progress_callback=lambda stage, progress: self._update(job_id, stage, progress),
            )
        except Exception:
            self._update(job_id, "failed", 100, error="Repository indexing failed.")
            return
        self._update(job_id, "ready", 100, summary=summary)

    def _update(
        self,
        job_id: str,
        status: JobStatus,
        progress: int,
        summary: IndexingSummary | None = None,
        error: str | None = None,
    ) -> None:
        with self.lock:
            job = self.jobs[job_id]
            job.status = status
            job.progress = progress
            job.summary = summary or job.summary
            job.error = error
