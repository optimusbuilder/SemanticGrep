from pathlib import Path

from app.chunking import MAX_EMBED_TOKENS, chunk_source_file
from app.models import SourceFile
from app.repository import collect_source_files, repository_name


def test_repository_name_strips_git_suffix() -> None:
    url = "https://github.com/browserbase/stagehand.git"
    assert repository_name(url) == "browserbase/stagehand"


def test_collect_source_files_only_includes_production_code(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "src" / "app.ts").write_text("export const app = true;", encoding="utf-8")
    (tmp_path / "main.py").write_text("print('production')", encoding="utf-8")
    (tmp_path / "node_modules" / "ignored.js").write_text("ignored", encoding="utf-8")
    (tmp_path / "tests" / "app.test.ts").write_text("ignored", encoding="utf-8")
    (tmp_path / "docs" / "guide.md").write_text("# ignored", encoding="utf-8")
    (tmp_path / "src" / "generated.ts").write_text("// @generated\nexport {}", encoding="utf-8")
    (tmp_path / "src" / "types.d.ts").write_text("declare type Ignored = string", encoding="utf-8")
    (tmp_path / "asset.png").write_bytes(b"png")

    source_files = collect_source_files(tmp_path)

    assert [(source.path, source.language) for source in source_files] == [
        ("main.py", "python"),
        ("src/app.ts", "typescript"),
    ]


def test_collect_source_files_skips_minified_javascript(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "bundle.js").write_text("x" * 10_001, encoding="utf-8")
    (tmp_path / "src" / "app.js").write_text("export const app = true;", encoding="utf-8")

    source_files = collect_source_files(tmp_path)

    assert [source.path for source in source_files] == ["src/app.js"]


def test_chunking_uses_line_overlap() -> None:
    source_file = SourceFile(
        path="src/example.py",
        content="\n".join(f"line_{number}" for number in range(1, 96)),
        language="python",
    )

    chunks = chunk_source_file(source_file)

    assert [(chunk.start_line, chunk.end_line) for chunk in chunks] == [(1, 50), (41, 90), (81, 95)]


def test_chunking_splits_text_that_exceeds_provider_token_limit() -> None:
    source_file = SourceFile(path="src/large.py", content="x" * 2_000, language="python")

    chunks = chunk_source_file(source_file, token_count=lambda text: len(text))

    assert len(chunks) > 1
    assert all(len(chunk.content) <= MAX_EMBED_TOKENS for chunk in chunks)
    assert {(chunk.start_line, chunk.end_line) for chunk in chunks} == {(1, 1)}
