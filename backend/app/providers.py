import time
from collections import deque
from collections.abc import Callable, Iterator, Sequence

import cohere
from cohere.errors import TooManyRequestsError
from pinecone import Pinecone, ServerlessSpec
from pinecone.errors.exceptions import NotFoundError

from app.config import Settings
from app.models import CodeChunk

EMBED_MODEL = "embed-english-v3.0"
EMBED_BATCH_SIZE = 96
EMBED_BATCH_TOKEN_LIMIT = 20_000
EMBED_DIMENSION = 1_024
UPSERT_BATCH_SIZE = 100


def batches[T](items: Sequence[T], size: int) -> Iterator[Sequence[T]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


class CohereEmbedder:
    def __init__(self, api_key: str, tokens_per_minute: int) -> None:
        self.client = cohere.ClientV2(api_key=api_key)
        self.tokens_per_minute = tokens_per_minute
        self.request_history: deque[tuple[float, int]] = deque()

    def count_tokens(self, text: str) -> int:
        return len(self.client.tokenize(text=text, model=EMBED_MODEL, offline=True).tokens)

    def embed_documents(
        self,
        chunks: Sequence[CodeChunk],
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> tuple[list[list[float]], float]:
        embeddings: list[list[float]] = []
        started_at = time.perf_counter()
        completed = 0
        token_safe_batches = list(self._token_safe_batches(chunks))
        for batch, token_count in token_safe_batches:
            self._wait_for_rate_limit(token_count)
            try:
                response = self.client.embed(
                    model=EMBED_MODEL,
                    input_type="search_document",
                    texts=[chunk.content for chunk in batch],
                    embedding_types=["float"],
                    truncate="NONE",
                )
            except TooManyRequestsError:
                # A provider-side window can be stricter than the configured allowance.
                time.sleep(60)
                self.request_history.clear()
                response = self.client.embed(
                    model=EMBED_MODEL,
                    input_type="search_document",
                    texts=[chunk.content for chunk in batch],
                    embedding_types=["float"],
                    truncate="NONE",
                )
            if response.embeddings.float is None:
                raise RuntimeError("Cohere did not return float embeddings.")
            embeddings.extend(response.embeddings.float)
            completed += len(batch)
            if progress_callback is not None:
                progress_callback(completed, len(chunks))
        return embeddings, time.perf_counter() - started_at

    def _token_safe_batches(
        self, chunks: Sequence[CodeChunk]
    ) -> Iterator[tuple[list[CodeChunk], int]]:
        batch: list[CodeChunk] = []
        batch_tokens = 0
        for chunk in chunks:
            chunk_tokens = self.count_tokens(chunk.content)
            if batch and (
                len(batch) == EMBED_BATCH_SIZE
                or batch_tokens + chunk_tokens > EMBED_BATCH_TOKEN_LIMIT
            ):
                yield batch, batch_tokens
                batch, batch_tokens = [], 0
            batch.append(chunk)
            batch_tokens += chunk_tokens
        if batch:
            yield batch, batch_tokens

    def _wait_for_rate_limit(self, request_tokens: int) -> None:
        while True:
            now = time.monotonic()
            while self.request_history and now - self.request_history[0][0] >= 60:
                self.request_history.popleft()
            used_tokens = sum(token_count for _, token_count in self.request_history)
            if used_tokens + request_tokens <= self.tokens_per_minute:
                self.request_history.append((now, request_tokens))
                return
            wait_seconds = 60 - (now - self.request_history[0][0])
            time.sleep(max(wait_seconds, 0))


class PineconeStore:
    def __init__(self, settings: Settings) -> None:
        self.client = Pinecone(api_key=settings.pinecone_api_key)
        self.index_name = settings.pinecone_index_name
        self.cloud = settings.pinecone_cloud
        self.region = settings.pinecone_region

    def _index(self):
        index_names = self.client.list_indexes().names()
        if self.index_name not in index_names:
            self.client.create_index(
                name=self.index_name,
                dimension=EMBED_DIMENSION,
                metric="cosine",
                spec=ServerlessSpec(cloud=self.cloud, region=self.region),
            )
        description = self.client.describe_index(self.index_name)
        if description.dimension != EMBED_DIMENSION:
            raise RuntimeError(
                f"Pinecone index {self.index_name!r} must use {EMBED_DIMENSION} dimensions."
            )
        return self.client.Index(host=description.host)

    def replace_repository(
        self,
        repository: str,
        chunks: Sequence[CodeChunk],
        embeddings: Sequence[list[float]],
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("Every chunk must have exactly one embedding.")
        index = self._index()
        namespace = repository.replace("/", "--")
        try:
            index.delete(delete_all=True, namespace=namespace)
        except NotFoundError:
            # Pinecone returns 404 when a namespace has not been indexed before.
            pass
        vectors = [
            {
                "id": chunk.id,
                "values": embedding,
                "metadata": {
                    "repository": chunk.repository,
                    "file_path": chunk.file_path,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "language": chunk.language,
                    "content": chunk.content,
                },
            }
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]
        completed = 0
        for batch in batches(vectors, UPSERT_BATCH_SIZE):
            index.upsert(vectors=list(batch), namespace=namespace)
            completed += len(batch)
            if progress_callback is not None:
                progress_callback(completed, len(vectors))
