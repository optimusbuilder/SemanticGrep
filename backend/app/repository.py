from pathlib import Path

from app.models import SourceFile

SUPPORTED_EXTENSIONS = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".cpp": "cpp",
    ".c": "c",
    ".hpp": "cpp",
    ".h": "c",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".md": "markdown",
}
IGNORED_DIRECTORIES = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "vendor",
    "target",
    "__pycache__",
    ".next",
}
MAX_FILE_SIZE_BYTES = 1_000_000


def repository_name(github_url: str) -> str:
    """Return the stable owner/repository identifier from a validated GitHub URL."""
    parts = [part for part in github_url.rstrip("/").split("/") if part]
    owner, repository = parts[-2:]
    return f"{owner}/{repository.removesuffix('.git')}"


def collect_source_files(repository_root: Path) -> list[SourceFile]:
    source_files: list[SourceFile] = []
    for path in repository_root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        relative_path = path.relative_to(repository_root)
        if any(part in IGNORED_DIRECTORIES for part in relative_path.parts):
            continue
        language = SUPPORTED_EXTENSIONS.get(path.suffix.lower())
        if language is None or path.stat().st_size > MAX_FILE_SIZE_BYTES:
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        if content.strip():
            source_files.append(
                SourceFile(path=relative_path.as_posix(), content=content, language=language)
            )
    return source_files
