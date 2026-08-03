import re
from collections import defaultdict
from collections.abc import Iterable

from app.models import CodeChunk, SourceFile

CORE_SOURCE_DIRECTORIES = {"app", "cmd", "internal", "lib", "pkg", "src"}
BARREL_LINE = re.compile(r"^(?:import\s.+|export\s+(?:\*|\{).+|//.*|/\*.*|\*/)$")


def prioritize_source_files(source_files: Iterable[SourceFile]) -> list[SourceFile]:
    return sorted(
        source_files,
        key=lambda source_file: (_source_priority(source_file.path), source_file.path),
    )


def select_index_chunks(
    chunks: Iterable[CodeChunk], max_chunks: int | None
) -> tuple[list[CodeChunk], int]:
    all_chunks = list(chunks)
    high_signal_chunks = [chunk for chunk in all_chunks if _is_high_signal(chunk)]
    if max_chunks is None or len(high_signal_chunks) <= max_chunks:
        return high_signal_chunks, len(all_chunks) - len(high_signal_chunks)

    chunks_by_priority: dict[int, dict[str, list[CodeChunk]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for chunk in high_signal_chunks:
        chunks_by_priority[_source_priority(chunk.file_path)][chunk.file_path].append(chunk)

    selected: list[CodeChunk] = []
    for priority in sorted(chunks_by_priority):
        file_chunks = chunks_by_priority[priority]
        offsets = {path: 0 for path in file_chunks}
        while len(selected) < max_chunks:
            added_chunk = False
            for path in sorted(file_chunks):
                offset = offsets[path]
                if offset >= len(file_chunks[path]):
                    continue
                selected.append(file_chunks[path][offset])
                offsets[path] += 1
                added_chunk = True
                if len(selected) == max_chunks:
                    break
            if not added_chunk:
                break
        if len(selected) == max_chunks:
            break
    return selected, len(all_chunks) - len(selected)


def _source_priority(path: str) -> int:
    path_parts = set(path.split("/"))
    if path_parts & CORE_SOURCE_DIRECTORIES:
        return 0
    if "packages" in path_parts:
        return 1
    if "/" not in path:
        return 2
    return 3


def _is_high_signal(chunk: CodeChunk) -> bool:
    lines = [line.strip() for line in chunk.content.splitlines() if line.strip()]
    if len(chunk.content.strip()) < 48 or not lines:
        return False
    return not all(BARREL_LINE.match(line) for line in lines)
