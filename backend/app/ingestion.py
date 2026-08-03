import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from git import Repo

from app.chunking import chunk_source_files
from app.config import Settings
from app.providers import CohereEmbedder, PineconeStore
from app.repository import collect_source_files, repository_name
from app.selection import prioritize_source_files, select_index_chunks

ProgressCallback = Callable[[str, int], None]


@dataclass(frozen=True)
class IndexingSummary:
    repository: str
    files: int
    chunks: int
    available_chunks: int
    skipped_chunks: int
    embedding_time_seconds: float


class RepositoryIndexer:
    def __init__(self, settings: Settings) -> None:
        self.embedder = CohereEmbedder(
            settings.cohere_api_key,
            settings.cohere_tokens_per_minute,
        )
        self.store = PineconeStore(settings)

    def index(
        self,
        github_url: str,
        max_chunks: int | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> IndexingSummary:
        repository = repository_name(github_url)
        _report_progress(progress_callback, "cloning", 5)
        with tempfile.TemporaryDirectory(prefix="semanticgrep-") as directory:
            checkout = Path(directory) / "repository"
            Repo.clone_from(github_url, checkout, depth=1)
            source_files = collect_source_files(checkout)
            _report_progress(progress_callback, "filtering", 20)
            chunks = chunk_source_files(
                prioritize_source_files(source_files), repository, self.embedder.count_tokens
            )

        if not chunks:
            raise ValueError(
                "The repository did not contain any supported, non-empty source files."
            )
        _report_progress(progress_callback, "chunking", 35)
        available_chunks = len(chunks)
        chunks, skipped_chunks = select_index_chunks(chunks, max_chunks)
        if not chunks:
            raise ValueError("The repository did not contain any high-signal source-code chunks.")

        embeddings, embedding_time = self.embedder.embed_documents(
            chunks,
            progress_callback=lambda completed, total: _report_progress(
                progress_callback, "embedding", 40 + int((completed / total) * 45)
            ),
        )
        self.store.replace_repository(
            repository,
            chunks,
            embeddings,
            progress_callback=lambda completed, total: _report_progress(
                progress_callback, "upserting", 85 + int((completed / total) * 14)
            ),
        )
        return IndexingSummary(
            repository=repository,
            files=len(source_files),
            chunks=len(chunks),
            available_chunks=available_chunks,
            skipped_chunks=skipped_chunks,
            embedding_time_seconds=round(embedding_time, 2),
        )


def _report_progress(
    progress_callback: ProgressCallback | None, stage: str, progress: int
) -> None:
    if progress_callback is not None:
        progress_callback(stage, progress)
