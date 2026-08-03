from collections.abc import Callable
from uuid import NAMESPACE_URL, uuid5

from app.models import CodeChunk, SourceFile

CHUNK_LINES = 50
CHUNK_OVERLAP_LINES = 10
# Cohere reserves four tokens for the search_document input type.
MAX_EMBED_TOKENS = 508

TokenCounter = Callable[[str], int]


def _default_token_count(text: str) -> int:
    # Conservative for source code, where tokens are often shorter than prose tokens.
    return (len(text) + 2) // 3


def _split_to_token_limit(
    lines: list[str], token_count: TokenCounter, line_offset: int = 0
) -> list[tuple[list[str], int, int]]:
    if not lines:
        return []
    text = "\n".join(lines)
    if token_count(text) <= MAX_EMBED_TOKENS:
        return [(lines, line_offset, len(lines))]
    if len(lines) == 1:
        # Preserve the source line while binary-searching a provider-safe substring size.
        segments: list[tuple[list[str], int, int]] = []
        character_offset = 0
        while character_offset < len(lines[0]):
            low, high, best = character_offset + 1, len(lines[0]), character_offset
            while low <= high:
                midpoint = (low + high) // 2
                if token_count(lines[0][character_offset:midpoint]) <= MAX_EMBED_TOKENS:
                    best = midpoint
                    low = midpoint + 1
                else:
                    high = midpoint - 1
            if best == character_offset:
                raise ValueError("A source-code character exceeds Cohere's embedding token limit.")
            segments.append(([lines[0][character_offset:best]], line_offset, 1))
            character_offset = best
        return segments

    midpoint = len(lines) // 2
    left = _split_to_token_limit(lines[:midpoint], token_count, line_offset)
    right = _split_to_token_limit(lines[midpoint:], token_count, line_offset + midpoint)
    return left + right


def chunk_source_file(
    source_file: SourceFile, token_count: TokenCounter = _default_token_count
) -> list[CodeChunk]:
    lines = source_file.content.splitlines()
    chunks: list[CodeChunk] = []
    step = CHUNK_LINES - CHUNK_OVERLAP_LINES

    for start in range(0, len(lines), step):
        window = lines[start : start + CHUNK_LINES]
        if not window:
            break
        segments = _split_to_token_limit(window, token_count)
        for segment, line_offset, line_span in segments:
            content = "\n".join(segment)
            if not content:
                continue
            segment_start = start + line_offset + 1
            segment_end = segment_start + line_span - 1
            identifier = uuid5(
                NAMESPACE_URL,
                f"{source_file.path}:{segment_start}:{segment_end}:{content}",
            )
            chunks.append(
                CodeChunk(
                    id=str(identifier),
                    repository="",
                    file_path=source_file.path,
                    start_line=segment_start,
                    end_line=segment_end,
                    language=source_file.language,
                    content=content,
                )
            )
        if start + CHUNK_LINES >= len(lines):
            break
    return chunks


def chunk_source_files(
    source_files: list[SourceFile],
    repository: str,
    token_count: TokenCounter = _default_token_count,
) -> list[CodeChunk]:
    chunks: list[CodeChunk] = []
    for source_file in source_files:
        chunks.extend(
            CodeChunk(
                id=chunk.id,
                repository=repository,
                file_path=chunk.file_path,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                language=chunk.language,
                content=chunk.content,
            )
            for chunk in chunk_source_file(source_file, token_count)
        )
    return chunks
