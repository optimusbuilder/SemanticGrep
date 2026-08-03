# RepoRanker API

FastAPI service for RepoRanker's code retrieval pipeline. It ingests public GitHub repositories, stores embeddings in Pinecone, retrieves and reranks candidates with Cohere, and generates grounded answers with citations.

## Development

The API loads secrets from the repository-root `.env` file.

```bash
uv sync --all-groups
uv run fastapi dev app/main.py
```

Run checks with:

```bash
uv run ruff check .
uv run pytest
```

Open http://localhost:8000/docs for the interactive API schema. See the root [README](../README.md) for architecture, API details, and deployment setup.
