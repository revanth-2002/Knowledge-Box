# Knowledge Inbox

Save notes and URLs, then ask questions across everything you've saved. A
minimal RAG (retrieval-augmented generation) app: FastAPI backend, React
frontend, SQLite storage, OpenAI for embeddings + answer generation.

## Project layout

```
knowledge-inbox/
├── backend/     FastAPI app (Python)
└── frontend/    React app (Vite)
```

## Quick start

### Backend

```bash
cd backend
python3 -m venv venv && source venv/bin/activate   # optional but recommended
pip install -r requirements.txt
cp .env.example .env
# edit .env and set OPENAI_API_KEY=sk-...
python3 -m uvicorn app.main:app --reload --port 8000
```

The API is now at `http://localhost:8000`. Interactive docs at
`http://localhost:8000/docs`. A `knowledge_inbox.db` SQLite file is
created automatically on first run.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The dev server proxies `/api/*` to the
backend at `localhost:8000` (see `vite.config.js`), so both must be
running.

### Running tests

```bash
cd backend
pytest tests/ -v
```

Covers the chunking service (pure logic, no API key required). Ingestion
and RAG flows were verified end-to-end with the OpenAI client mocked;
add live-integration tests behind a `RUN_LIVE_TESTS` flag if you want to
exercise real API calls in CI.

## API

| Method | Path      | Purpose                                      |
|--------|-----------|-----------------------------------------------|
| POST   | `/ingest` | Save a note or URL (fetches + chunks + embeds) |
| GET    | `/items`  | List saved items, paginated, newest first     |
| POST   | `/query`  | Ask a question, get an answer + cited sources |
| GET    | `/health` | Liveness check                                 |

## Design decisions & tradeoffs

**Chunking — fixed-size sliding window, not semantic chunking.**
Chosen for predictability and because it works uniformly on both
freeform notes and scraped HTML text without a second model call to
segment. Tradeoff: it can split mid-sentence/mid-idea, which can hurt
retrieval precision on content with strong internal structure. A
production version would chunk on paragraph/heading boundaries first,
falling back to fixed windows only for oversized paragraphs.

**Vector storage — SQLite + brute-force cosine similarity (numpy), not
a vector DB.** At the expected scale (one user, personal notes/links —
likely low thousands of chunks) a linear scan is fast (single-digit ms)
and needs zero extra infrastructure. It's an intentional shortcut, not
an oversight.
*What breaks at scale:* once the corpus grows past roughly 10⁵ chunks,
per-query latency grows linearly and every query loads the full
embedding matrix into memory. The fix is a real ANN index — pgvector
with HNSW, Qdrant, or similar — with persistent indexing instead of
recomputing similarity per request.

**URL fetching — server-side, not client-side.** Keeps CORS and
authentication headaches off the frontend, and lets us cap payload size
and timeout centrally. `readability-lxml` extracts the main article
body; falls back to a stripped BeautifulSoup text dump if that fails.

**Error handling.** Domain exceptions (`FetchError`, `EmbeddingError`,
`LLMError`, `ValidationError`) live in `app/core/errors.py` and are
raised from services, which keeps services framework-agnostic. A single
FastAPI exception handler maps them to a consistent JSON error envelope
(`{"error": {"code", "message", "detail"}}`), plus a catch-all handler
for anything unexpected.

**Logging.** JSON structured logs (one object per line) via a custom
formatter, with a request-scoped `request_id` injected by middleware and
per-stage fields (`stage`, `chunk_count`, `duration_ms`, etc.) at
individual log sites — set up so this could be piped straight into any
log aggregator without reformatting.

**What else would change for production:**
- Auth (currently single-tenant, no login)
- Background job queue for ingestion (Celery/RQ) instead of blocking the
  request on fetch + embed
- Rate limiting and retry/backoff tuning on the OpenAI calls (a basic
  retry with exponential backoff is already in place for connection
  errors)
- Connection pooling / a real database (Postgres) once concurrent writes
  matter
- Observability: tracing across ingest → embed → retrieve → generate,
  not just log lines
