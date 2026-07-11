# Tradeoffs

Decisions made for this project's scope (single user, take-home
timeframe), and what each one costs — plus what I'd change first if this
had to run in production.

## Chunking: fixed-size sliding window, not semantic chunking

**What it is:** `services/chunking.py` splits text into fixed-size
word-count windows (default 500 words, 50-word overlap), regardless of
sentence or paragraph boundaries.

**Why:** It's predictable, easy to debug, and works uniformly on both
freeform notes (which may have no paragraph structure at all) and
scraped article text, without a second model call to segment first. The
overlap preserves context that would otherwise be lost at a boundary.

**Cost:** It can and does split mid-sentence or mid-idea, which hurts
retrieval precision on content with strong internal structure — a
chunk boundary landing in the middle of a key sentence means that
sentence is diluted across two less-relevant chunks instead of living
whole in one strongly-relevant chunk.

**Production fix:** Chunk on paragraph/heading boundaries first, and
only fall back to fixed-size windows for individual paragraphs that
exceed the size budget. For structured sources (articles with real
HTML headings), use the heading hierarchy to also attach section
context to each chunk.

## Vector storage: SQLite + brute-force cosine similarity, not a vector DB

**What it is:** Embeddings are stored as JSON-encoded float arrays in a
SQLite TEXT column. At query time, `services/vector_store.py` loads
matching chunk rows, stacks their embeddings into a numpy matrix, and
computes cosine similarity against the query vector in one vectorized
op — an O(n) scan, not an indexed lookup.

**Why:** Zero extra infrastructure to run, and at the expected scale —
one user's personal notes and saved links, realistically low thousands
of chunks — a linear scan is fast (single-digit milliseconds) and
simpler to reason about than standing up and operating a vector
database for a take-home project.

**Cost:** This is the single biggest thing that would need to change
for real-world scale.

- Latency grows linearly with corpus size — fine at 10³ chunks, a
  real problem well before 10⁶.
- Every query loads the full set of candidate embeddings into memory;
  there's no persistent index, so there's no amortized cost of
  indexing — you pay the full scan every time.
- `max_similarity_candidates` in `config.py` is a hard cap (default 2000) precisely because past that point this approach stops being
  "good enough" even for a demo.

**Production fix:** A real ANN (approximate nearest neighbor) index —
pgvector with an HNSW index if you're already on Postgres, or a
dedicated vector database (Qdrant, Weaviate, Pinecone) if retrieval
becomes a first-class scaling concern. Both give sub-linear query time
and persistent indexing instead of recompute-per-query.

## URL fetching: server-side, not client-side

**What it is:** The backend fetches URLs itself (`services/fetcher.py`,
via `httpx`), rather than asking the browser to fetch and send back the
page content.

**Why:** Avoids CORS entirely (many sites block cross-origin fetches
from a browser), keeps a single place to enforce timeouts and payload
size caps (`fetch_timeout_seconds`, `max_fetch_bytes` in `config.py`),
and means the extraction logic (readability-lxml, with a BeautifulSoup
fallback) only has to be written once.

**Cost:** The backend is now doing outbound network calls to
arbitrary URLs on the user's behalf, which is a real SSRF surface in a
multi-tenant deployment — a malicious input could ask the server to
fetch internal-network addresses.

**Production fix:** Validate/deny-list resolved IPs before fetching
(block RFC1918 ranges, link-local, etc.), and consider routing
outbound fetches through an isolated egress proxy.

## Error handling: typed domain exceptions, not inline HTTPException

**What it is:** Services raise typed exceptions (`FetchError`,
`EmbeddingError`, `LLMError`, `ValidationError`) defined in
`core/errors.py`; a single FastAPI exception handler maps them to a
consistent JSON envelope.

**Why:** Keeps services importable and testable without FastAPI in the
loop (see `tests/test_chunking.py`, which never touches the API layer),
and guarantees every error the client sees has the same shape,
regardless of which layer raised it.

**Cost:** One more layer of indirection versus just raising
`HTTPException` directly in route handlers — a bit more boilerplate for
a project this size.

## Synchronous ingestion, not a background job queue

**What it is:** `POST /ingest` blocks on fetch → chunk → embed →
persist and returns only once everything is done.

**Why:** Simpler to reason about and test; the client gets an immediate,
definitive success/failure instead of having to poll a job status.

**Cost:** A slow URL fetch or a slow embeddings call makes the whole
request slow, and there's no retry path if the client's connection
drops mid-request — the ingestion has to be resubmitted from scratch.

**Production fix:** Move fetch+embed into a background worker (Celery,
RQ, or a simple task queue), return a `202 Accepted` with a job id
immediately, and let the frontend poll or subscribe for completion.

## Retry policy: exponential backoff only on connection errors

**What it is:** `services/embeddings.py` retries up to 3 times with
exponential backoff, but only for `APIConnectionError` — a 4xx/5xx
`APIError` from OpenAI is surfaced immediately as an `EmbeddingError`.

**Why:** Retrying a connection blip (DNS hiccup, transient network
failure) is almost always correct. Retrying a 429 or 500 blindly
without honoring `Retry-After` can make rate-limiting worse, and
retrying a 400 (bad request) is never going to succeed.

**Cost:** No `Retry-After`-aware backoff on rate limits yet, so a burst
of 429s from OpenAI will surface as user-facing errors rather than being
smoothed over.

**Production fix:** Add explicit 429 handling that reads `Retry-After`
and requeues rather than failing the request outright, especially once
ingestion moves to a background queue (see above).

## Single-tenant, no auth

**What it is:** There's no login, no user scoping — every item and
every query operates over the entire database.

**Why:** Out of scope for the assignment; the point was RAG mechanics,
not an auth system.

**Cost:** Not deployable as a shared/public app as-is.

**Production fix:** Add a `user_id` column to `Item`, scope every query
in `api/` and `services/` by the authenticated user, and put real auth
(session or JWT) in front of the API.
