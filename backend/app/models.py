from dataclasses import dataclass


@dataclass(frozen=True)
class SourceFile:
    path: str
    content: str
    language: str


@dataclass(frozen=True)
class CodeChunk:
    id: str
    repository: str
    file_path: str
    start_line: int
    end_line: int
    language: str
    content: str
