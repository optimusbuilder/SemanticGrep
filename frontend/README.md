# SemanticGrep Frontend

Next.js interface for selecting a repository, running semantic code searches, reviewing vector-versus-reranked results, and reading grounded answers.

## Development

```bash
npm install
cp .env.example .env.local
npm run dev
```

Set `NEXT_PUBLIC_API_URL` in `.env.local` to the FastAPI service URL. The local default is `http://localhost:8000`.

```bash
npm run lint
npm run build
```

See the root [README](../README.md) for the full architecture and deployment guide.
