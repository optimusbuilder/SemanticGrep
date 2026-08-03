from app.models import CodeChunk, SourceFile
from app.selection import prioritize_source_files, select_index_chunks


def _chunk(file_path: str, content: str, start_line: int = 1) -> CodeChunk:
    return CodeChunk(
        id=f"{file_path}-{start_line}",
        repository="example/repository",
        file_path=file_path,
        start_line=start_line,
        end_line=start_line + 4,
        language="typescript",
        content=content,
    )


def test_prioritize_source_files_prefers_source_roots() -> None:
    source_files = [
        SourceFile(path="vite.config.ts", content="export default {}", language="typescript"),
        SourceFile(path="packages/core/index.ts", content="export {}", language="typescript"),
        SourceFile(path="src/main.ts", content="export {}", language="typescript"),
    ]

    prioritized = prioritize_source_files(source_files)

    assert [source_file.path for source_file in prioritized] == [
        "src/main.ts",
        "packages/core/index.ts",
        "vite.config.ts",
    ]


def test_fast_selection_round_robins_across_high_priority_files() -> None:
    implementation = "export async function run() { await browser.launch(); return true; }"
    chunks = [
        _chunk("src/a.ts", implementation, 1),
        _chunk("src/a.ts", implementation, 41),
        _chunk("src/b.ts", implementation, 1),
        _chunk("config.ts", implementation, 1),
        _chunk("src/index.ts", 'export { Stagehand } from "./stagehand";'),
    ]

    selected, skipped = select_index_chunks(chunks, max_chunks=3)

    assert [(chunk.file_path, chunk.start_line) for chunk in selected] == [
        ("src/a.ts", 1),
        ("src/b.ts", 1),
        ("src/a.ts", 41),
    ]
    assert skipped == 2
