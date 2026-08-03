import tempfile
from dataclasses import dataclass
from pathlib import Path

from git import Repo

from app.chunking import chunk_source_files
from app.config import Settings
from app.providers import CohereEmbedder, PineconeStore
from app.repository import collect_source_files, repository_name


@dataclass(frozen=True)
class IndexingSummary:
    repository: str
    files: int
    chunks: int
    embedding_time_seconds: float


class RepositoryIndexer:
    def __init__(self, settings: Settings) -> None:
        self.embedder = CohereEmbedder(
            settings.cohere_api_key,
            settings.cohere_tokens_per_minute,
        )
        self.store = PineconeStore(settings)

    def index(self, github_url: str) -> IndexingSummary:
        repository = repository_name(github_url)
        with tempfile.TemporaryDirectory(prefix="reporanker-") as directory:
            checkout = Path(directory) / "repository"
            Repo.clone_from(github_url, checkout, depth=1)
            source_files = collect_source_files(checkout)
            chunks = chunk_source_files(source_files, repository, self.embedder.count_tokens)

        if not chunks:
            raise ValueError(
                "The repository did not contain any supported, non-empty source files."
            )

        embeddings, embedding_time = self.embedder.embed_documents(chunks)
        self.store.replace_repository(repository, chunks, embeddings)
        return IndexingSummary(
            repository=repository,
            files=len(source_files),
            chunks=len(chunks),
            embedding_time_seconds=round(embedding_time, 2),
        )
