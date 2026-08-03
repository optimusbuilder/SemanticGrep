# SemanticGrep

**SemanticGrep is an end-to-end retrieval pipeline for source code.** It indexes a public GitHub repository, retrieves implementation-relevant code with semantic search, improves precision with reranking, and generates grounded explanations with source citations.

Live demo: https://reporanker-ten.vercel.app

## Why SemanticGrep

Keyword search can find a symbol, but it struggles with intent. SemanticGrep is designed for questions such as:

- Where is clipboard handling implemented?
- How does agent replay recording work?
- Where are screenshots captured after agent actions?
- How does Stagehand launch Chromium?

The project demonstrates the retrieval pattern behind modern AI search:

```text
GitHub repository
  -> production-code filtering
  -> line-aware, token-safe chunks
  -> Cohere Embed
  -> Pinecone vector search (top 20)
  -> Cohere Rerank (top 5)
  -> Cohere Command A grounded explanation
```

## Features

- Public GitHub repository ingestion with fast and full modes
- Production-code-first filtering to avoid docs, tests, generated code, minified assets, and build output
- 50-line chunks with 10-line overlap and Cohere-safe token splitting
- Cohere `embed-english-v3.0` document and query embeddings
- One Pinecone namespace per repository, keeping searches isolated
- Cohere `rerank-english-v3.0` comparison against raw vector retrieval
- Cohere Command A explanations grounded only in reranked code context
- Clickable source citations, GitHub deep links, copyable snippets, and language filters
- Repository workspace for Stagehand, existing indexes, and new GitHub repositories
- Guided Browserbase Stagehand queries and a Retrieval Lab showing rank movement
- Curated Stagehand benchmark comparing vector-only and reranked `Recall@5` and MRR

## Architecture

```text
                         Indexing

GitHub URL -> shallow clone -> source filtering -> chunking
                                              |
                                              v
                               Cohere Embed (search_document)
                                              |
                                              v
                            Pinecone namespace: owner--repository

                          Query-time retrieval

Natural-language query -> Cohere Embed (search_query)
                                              |
                                              v
                              Pinecone similarity search (top 20)
                                              |
                                              v
                               Cohere Rerank (top 5 candidates)
                                              |
                                              v
                         Command A grounded answer + citations
```

## Retrieval Design

SemanticGrep uses one 1,024-dimensional Pinecone index. Each repository is stored in its own namespace, derived from `owner/repository`. For example, `browserbase/stagehand` becomes `browserbase--stagehand`.

Fast indexing prioritizes implementation source roots such as `src/`, `app/`, `lib/`, and `packages/*/src/`. It removes low-signal chunks and caps the first run at 2,000 chunks to keep trial usage and first-run latency practical.

The default Stagehand dry run selected 606 production files and 2,000 high-signal chunks from 3,795 eligible chunks.

## Benchmark

The built-in Stagehand benchmark evaluates five curated implementation queries. Both conditions begin with the same Pinecone top-20 candidate pool:

- Vector-only reports the top five vector matches.
- Reranked uses Cohere Rerank to select the top five candidates.

On the current Stagehand index, the benchmark measured:

| Metric | Vector-only | Cohere Rerank |
| --- | ---: | ---: |
| Recall@5 | 40% | 60% |
| MRR | 0.306 | 0.340 |

These are curated demo-evaluation results, not a claim of universal code-search performance.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js, TypeScript, Tailwind CSS, react-markdown |
| Backend | Python 3.12+, FastAPI, Pydantic |
| Retrieval | Cohere Embed, Cohere Rerank, Cohere Command A, Pinecone |
| Ingestion | GitPython |
| Deployment | Vercel frontend, Railway backend |

## Local Setup

### 1. Configure environment variables

Create a root `.env` from `.env.example`:

```bash
COHERE_API_KEY=
PINECONE_API_KEY=
PINECONE_INDEX_NAME=
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1
FRONTEND_ORIGIN=http://localhost:3000
```

Optional values:

```bash
COHERE_TOKENS_PER_MINUTE=90000
COHERE_GENERATION_MODEL=command-a-03-2025
FAST_INDEX_MAX_CHUNKS=2000
```

### 2. Start the API

```bash
cd backend
uv sync --all-groups
uv run fastapi dev app/main.py
```

API docs are available at http://localhost:8000/docs.

### 3. Start the frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open http://localhost:3000.

## API

### `POST /api/index`

Starts a background indexing job.

```json
{
  "github_url": "https://github.com/browserbase/stagehand",
  "mode": "fast"
}
```

### `GET /api/index/{job_id}`

Returns indexing progress through clone, filtering, chunking, embedding, and Pinecone upsert stages.

### `GET /api/repositories`

Lists indexed repository namespaces and their vector counts for the workspace selector.

### `POST /api/search`

```json
{
  "query": "How does agent replay recording work?",
  "repository": "browserbase/stagehand",
  "language": "typescript"
}
```

Returns raw vector candidates, reranked results, per-stage latency, a grounded Command A answer, and source citations.

### `POST /api/benchmark`

Runs the curated Stagehand retrieval-only benchmark. It skips Command A so the comparison measures vector search and reranking only.

## Deployment

The repository is structured for separate deployments:

- `backend/` contains a Dockerfile and `railway.toml` for Railway.
- `frontend/` is a Next.js application for Vercel.

Set these production variables:

| Service | Variables |
| --- | --- |
| Railway | `COHERE_API_KEY`, `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`, `FRONTEND_ORIGIN` |
| Vercel | `NEXT_PUBLIC_API_URL` |

The Railway Docker image installs system Git because GitPython clones public repositories at indexing time.

## Project Structure

```text
backend/
  app/
    ingestion.py       # clone, filter, chunk, embed, and upsert
    search.py          # retrieve, rerank, and generate answers
    benchmark.py       # curated retrieval evaluation
    providers.py       # Cohere and Pinecone integrations
    jobs.py            # background indexing job state
  tests/
frontend/
  src/app/page.tsx     # retrieval workspace and demo experience
```

## License

MIT. See [LICENSE](LICENSE).
