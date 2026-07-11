# Architecture

## Overview

Knowledge Inbox is a single-user RAG (retrieval-augmented generation)
app: save notes or URLs, get them chunked and embedded automatically,
then ask questions and get answers grounded in—and cited from—what
you've saved.

```
┌─────────────┐        HTTP/JSON        ┌──────────────────┐
│   React     │ ──────────────────────► │     FastAPI       │
│  (Vite dev  │ ◄────────────────────── │     backend        │
│   server)   │                         │                    │
└─────────────┘                         └─────────┬──────────┘
                                                    │
                    ┌───────────────────────────────┼───────────────────────┐
                    │                                │                       │
              ┌─────▼─────┐                  ┌───────▼───────┐      ┌────────▼────────┐
              │  SQLite    │                  │  OpenAI API    │      │  Target URLs     │
              │ (items,    │                  │ (embeddings +  │      │ (fetched server-  │
              │  chunks)   │                  │  chat)         │      │  side via httpx)  │
              └────────────┘                  └────────────────┘      └───────────────────┘
```

## Request flow

### Ingestion (`POST /ingest`)

```
client
  → api/ingest.py            (validate payload shape via Pydantic)
    → services/ingestion.py  (orchestration)
        → services/fetcher.py     [only if source_type == "url"]
            httpx.get → readability-lxml extraction → BS4 fallback
        → services/chunking.py    (fixed-size sliding window)
        → services/embeddings.py (OpenAI embeddings, batched, retried)
        → models/db.py            (persist Item + Chunk rows)
  ← IngestResponse {id, title, chunk_count, created_at}
```

### Listing (`GET /items`)

```
client → api/items.py → models/db.py (paginated query, newest first)
       ← ItemListResponse {items[], total}
```

### Querying (`POST /query`)

```
client
  → api/query.py
    → services/rag.py
        → services/embeddings.py   (embed the question)
        → services/vector_store.py (cosine similarity over all stored
                                     chunk embeddings, top-k)
        → OpenAI chat completion   (answer grounded in retrieved chunks,
                                     numbered [1][2].. citations)
  ← QueryResponse {answer, sources[]}
```

## RAG architecture

The RAG pipeline has two independent halves that share the same
embedding model: **indexing** (runs at ingest time, once per item) and
**retrieval + generation** (runs at query time, once per question).

```
                              INDEXING  (POST /ingest)
  ┌──────────┐   ┌──────────────┐   ┌─────────────┐   ┌───────────────┐   ┌──────────┐
  │ raw text  │──►│   chunk      │──►│   embed      │──►│  persist       │──►│  SQLite   │
  │ (note or  │   │ fixed-size,  │   │  one OpenAI  │   │  Item + N      │   │  items,   │
  │ fetched   │   │ sliding win- │   │  call, batch │   │  Chunk rows    │   │  chunks   │
  │ URL text) │   │ dow w/overlap│   │  of texts    │   │  (embedding    │   │           │
  └──────────┘   └──────────────┘   └─────────────┘   │  as JSON)      │   └──────────┘
                                                        └───────────────┘

                          RETRIEVAL + GENERATION  (POST /query)
  ┌──────────┐   ┌──────────────┐   ┌──────────────┐   ┌───────────────┐   ┌──────────┐
  │ question  │──►│  embed query  │──►│  similarity   │──►│  build prompt │──►│  chat    │
  │  (text)   │   │  same OpenAI  │   │  search:       │   │  w/ numbered  │   │  model   │
  │           │   │  embedding    │   │  cosine sim.   │   │  context      │   │  call    │
  │           │   │  model        │   │  vs. every     │   │  excerpts     │   │  (grounded│
  │           │   │               │   │  stored chunk, │   │  [1] [2] ...  │   │  answer + │
  │           │   │               │   │  top-k=5       │   │               │   │  citations)│
  └──────────┘   └──────────────┘   └──────────────┘   └───────────────┘   └──────────┘
                                                                                    │
                                                                                    ▼
                                                                   QueryResponse { answer,
                                                                     sources: [{item_id, title,
                                                                     url, snippet, similarity}] }
```

### Why indexing and retrieval share one embedding model

Cosine similarity is only meaningful when the query vector and the
stored vectors live in the same embedding space. Both
`services/embeddings.py:embed_texts` (indexing) and
`embed_query` (retrieval) call the same `settings.embedding_model`
(`text-embedding-3-small`), so this is enforced by construction rather
than by convention — there's exactly one place the model name is
configured.

### Retrieval: brute-force top-k, not an ANN index

`services/vector_store.py:top_k_similar_chunks` loads candidate chunk
rows (capped by `max_similarity_candidates`), stacks their stored
embeddings into a numpy matrix, and computes cosine similarity against
the query vector in a single vectorized operation, then takes the
top-k highest-scoring chunks (`settings.top_k_chunks`, default 5). No
per-item filtering happens at this stage — retrieval is global across
every saved item, which is what makes cross-note questions ("what have
I saved about X across everything") work without the user having to
pick which item to search.

### Prompt construction and grounding

`services/rag.py:_build_context_block` numbers each retrieved chunk
`[1]`, `[2]`, … and prefixes it with its source item's title, then
hands the whole block to the model alongside a system prompt
(`_SYSTEM_PROMPT`) that instructs it to:

1. answer using **only** the provided context,
2. say so plainly if the context is insufficient rather than guessing,
3. cite claims inline as `[1]`, `[2]` matching the excerpt numbers,
4. stay concise.

This is what keeps answers grounded in the user's own saved content
instead of the model's general knowledge, and is also what makes the
`[1]`/`[2]` markers in the answer text line up with the `sources[]`
array in the response — the frontend's `AnswerCard` renders them as a
matching numbered list.

### Failure and edge-case handling in the pipeline

- **No saved content at all:** `answer_question` short-circuits before
  calling the LLM and returns a fixed "you don't have any saved content
  yet" message — avoids spending a chat completion call on a query that
  can't possibly be answered.
- **Embedding call fails:** raises `EmbeddingError` (502) rather than
  silently returning an empty/zero vector, so a failed embed never
  silently corrupts similarity rankings.
- **Chat completion fails:** raises `LLMError` (502); retrieval has
  already succeeded at this point, but we don't fall back to returning
  raw chunks unlabeled as an "answer" — a failed generation is reported
  as a failure, not disguised as a degraded success.
- **Irrelevant question (nothing relevant retrieved):** current
  behavior always returns the top-k chunks regardless of how low their
  similarity score is — there's no minimum-similarity cutoff yet. This
  is called out in `NEXT_IMPROVEMENTS.md`.

## Layering

```
api/        HTTP concerns only: request/response shape, status codes,
            wiring a request to the right service. No business logic.

services/   All business logic. Framework-agnostic — nothing here
            imports FastAPI. Each module owns one concern:
              fetcher.py     URL → clean text
              chunking.py    text → overlapping chunks
              embeddings.py  text → vectors (OpenAI, swappable)
              vector_store.py top-k similarity search
              ingestion.py   orchestrates fetch → chunk → embed → persist
              rag.py         orchestrates embed → retrieve → generate

models/     Data shape. db.py = SQLAlchemy ORM (storage).
            schemas.py = Pydantic (API contract). Kept separate
            deliberately so the API can evolve independently of storage.

core/       Cross-cutting concerns: structured logging, domain
            exceptions + their HTTP mapping. Nothing here is
            business-specific.
```

This separation is what lets `services/` be unit-tested without a
running server or a real OpenAI key (see `tests/test_chunking.py`), and
lets `api/` stay thin enough to read top-to-bottom as documentation of
what each endpoint does.

## Data model

```
Item                          Chunk
────────────────────          ────────────────────
id            (PK, uuid)      id             (PK, uuid)
source_type   note | url      item_id        (FK → Item.id)
title                         chunk_index
raw_content                   chunk_text
url           nullable        token_count
created_at                    embedding_json  (JSON-encoded float[])
                               ── 1 Item : N Chunk ──
```

Embeddings are stored as JSON-encoded arrays in a TEXT column rather
than a dedicated vector type — see `TRADEOFFS.md` for why that's an
acceptable choice at this scale and what it costs.

## Error handling model

Services raise typed exceptions (`FetchError`, `EmbeddingError`,
`LLMError`, `ValidationError`, `ItemNotFoundError` — all subclasses of
`AppError` in `core/errors.py`). A single FastAPI exception handler
converts any `AppError` into a consistent envelope:

```json
{ "error": { "code": "fetch_error", "message": "...", "detail": "..." } }
```

A catch-all handler covers anything unexpected so the client never sees
a raw traceback. This keeps error-shape decisions in one place instead
of scattered across route handlers.

## Observability

Every log line is a single JSON object (`core/logging.py`), and every
HTTP request gets a `request_id` (via middleware) that's attached to the
response headers and to every log line emitted while handling that
request. Individual pipeline stages (`ingest_start`, `chunk`, `embed`,
`persist`, `retrieve`, `generate`) log their own timing/counts, so a
single ingest or query can be traced end-to-end from the logs alone.

## Frontend

Plain React + Vite, no state management library — the app is small
enough that two custom hooks (`useItems`, `useQuery`) plus component
-local state cover everything. `api/client.js` is the only place that
knows about HTTP; components and hooks never call `fetch` directly.

```
App.jsx
├── NoteInput      → POST /ingest, auto-detects note vs. URL
├── ItemList       ← GET /items (via useItems)
├── QueryBox       → POST /query (via useQuery)
└── AnswerCard     ← renders answer + numbered source citations
```

The dev server proxies `/api/*` to `localhost:8000` (`vite.config.js`),
so the frontend never hardcodes the backend's origin.

## Why these technology choices

| Choice                     | Reason |
|-----------------------------|--------|
| FastAPI                    | Async-native, Pydantic validation built in, auto-generated OpenAPI docs at `/docs` for free |
| SQLite                     | Zero infrastructure for a single-user app; trivial to swap for Postgres later since access goes through SQLAlchemy |
| SQLite+numpy for vectors   | No extra service to run for the expected corpus size; see `TRADEOFFS.md` for the scale limit |
| React + Vite                | Fast dev loop, no build-config yak-shaving, matches the assignment's frontend requirement |
| OpenAI embeddings + chat   | Single provider for both, behind a thin interface (`services/embeddings.py`, `services/rag.py`) so it's swappable |