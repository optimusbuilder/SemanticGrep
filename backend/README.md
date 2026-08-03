# RepoRanker API

FastAPI service for RepoRanker's source-code retrieval pipeline. It is deliberately
independent of the Next.js app so it can deploy to Railway.

## Local development

The service loads provider credentials from the repository root `.env` file. Start
from `../.env.example`; never commit real credentials.

```bash
uv sync --all-groups
uv run fastapi dev app/main.py
```

Open `http://localhost:8000/docs` for the OpenAPI interface. `POST /api/index`
clones a public GitHub repository, filters and chunks source files, embeds them
with Cohere, and replaces that repository's Pinecone namespace. `POST /api/search`
is the next pipeline milestone.
