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
}
IGNORED_DIRECTORIES = {
    ".git",
    ".github",
    ".next",
    "__pycache__",
    "__snapshots__",
    "build",
    "coverage",
    "demo",
    "demos",
    "dist",
    "doc",
    "docs",
    "e2e",
    "example",
    "examples",
    "fixture",
    "fixtures",
    "integration",
    "mocks",
    "node_modules",
    "scripts",
    "snapshot",
    "snapshots",
    "target",
    "test",
    "tests",
    "vendor",
}
MAX_FILE_SIZE_BYTES = 250_000
GENERATED_MARKERS = ("@generated", "auto-generated", "code generated", "do not edit")


def repository_name(github_url: str) -> str:
    """Return the stable owner/repository identifier from a validated GitHub URL."""
    parts = [part for part in github_url.rstrip("/").split("/") if part]
    owner, repository = parts[-2:]
    return f"{owner}/{repository.removesuffix('.git')}"


def collect_source_files(repository_root: Path) -> list[SourceFile]:
    source_files: list[SourceFile] = []
    for path in sorted(repository_root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative_path = path.relative_to(repository_root)
        if any(part in IGNORED_DIRECTORIES for part in relative_path.parts):
            continue
        language = SUPPORTED_EXTENSIONS.get(path.suffix.lower())
        if (
            language is None
            or _is_non_production_file(path)
            or path.stat().st_size > MAX_FILE_SIZE_BYTES
        ):
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        if content.strip() and not _is_generated_or_minified(content):
            source_files.append(
                SourceFile(path=relative_path.as_posix(), content=content, language=language)
            )
    return source_files


def _is_non_production_file(path: Path) -> bool:
    name = path.name.lower()
    stem = path.stem.lower()
    return (
        name.endswith(".d.ts")
        or ".min." in name
        or ".spec." in name
        or ".test." in name
        or stem.startswith("test_")
        or stem.endswith("_test")
    )


def _is_generated_or_minified(content: str) -> bool:
    opening = "\n".join(content.splitlines()[:5]).lower()
    if any(marker in opening for marker in GENERATED_MARKERS):
        return True
    lines = content.splitlines()
    return len(lines) <= 2 and len(content) > 10_000
