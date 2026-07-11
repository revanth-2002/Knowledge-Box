# Next Improvements

This is forward-looking: things worth doing next, beyond the scope of
the take-home. (For shortcuts already made and their immediate
production fix, see `TRADEOFFS.md` — this file goes further, into
features and quality improvements that aren't just "undo the shortcut.")

## Retrieval quality

- **Minimum-similarity cutoff.** `top_k_similar_chunks` always returns
  its top-k regardless of how weak the best match is, so an
  off-topic question still gets handed 5 chunks of context and the
  model has to notice on its own that they're irrelevant. Add a
  similarity floor (or a "the retrieved content isn't relevant enough"
  branch) so the app can say "I don't have anything on that" instead
  of relying entirely on prompt instructions to catch it.
- **Semantic/structural chunking.** Move off fixed-size windows toward
  paragraph- and heading-aware chunking (see `TRADEOFFS.md`) so
  retrieved chunks are coherent units of meaning, not arbitrary word
  spans.
- **Hybrid search.** Combine embedding similarity with keyword/BM25
  search. Pure embedding search can miss exact-term matches (specific
  names, error codes, product SKUs) that a keyword search would catch
  immediately.
- **Re-ranking.** Retrieve a larger candidate set (e.g. top-20) with
  cheap cosine similarity, then re-rank the top few with a stronger
  cross-encoder or the LLM itself before generation — usually a solid
  precision boost over similarity search alone.
- **Query expansion / rewriting.** For short or ambiguous questions,
  have the model rewrite the query into a fuller search query before
  embedding it, which tends to improve recall.

## Scale

- **Real vector index** (pgvector/HNSW, Qdrant, etc.) once corpus size
  makes brute-force scanning too slow — the detailed cost/benefit is in
  `TRADEOFFS.md`.
- **Background ingestion queue** (Celery/RQ) so `POST /ingest` returns
  immediately with a job id instead of blocking on fetch + embed;
  frontend polls or subscribes for completion.
- **Postgres instead of SQLite** once there's real write concurrency to
  handle (multi-user, or heavy background ingestion).
- **Incremental re-indexing.** If the embedding model changes, there's
  currently no migration path — every chunk would need re-embedding.
  Worth adding a `embedding_model` column per chunk so a migration can
  run incrementally and mixed-model states are detectable.

## Features

- **Multi-user support with auth.** Currently single-tenant; add a
  `user_id` on `Item`, scope every query, put real auth in front of the
  API.
- **Item management.** No delete/edit/re-fetch endpoints yet — you can
  currently only add and list. Add `DELETE /items/{id}` and a "refresh"
  action for URLs whose source content has changed.
- **Tagging / collections.** Manually or automatically tag items so a
  user can scope a question to a subset ("just my work notes") instead
  of always searching everything.
- **Conversation memory.** `/query` is currently stateless — each
  question is independent. Supporting follow-up questions would need
  conversation history threaded into the prompt, plus decisions about
  how much of that history to keep grounded vs. treated as new context
  to retrieve against.
- **File uploads.** Right now only notes and URLs are supported.
  PDFs, plain text files, and Markdown files are natural next input
  types — mostly an extension of the existing ingestion pipeline
  (parse → same chunk/embed/persist flow).
- **Streaming answers.** `/query` currently waits for the full chat
  completion before responding. Streaming the answer token-by-token
  (SSE or chunked response) would noticeably improve perceived latency
  in the UI.

## Reliability & ops

- **Rate-limit-aware retries.** Current retry logic (see
  `TRADEOFFS.md`) only handles connection errors; add `Retry-After`
  handling for 429s from OpenAI.
- **Idempotent ingestion / dedup.** Saving the same URL twice currently
  creates two separate items with duplicate chunks. Add a uniqueness
  check (by URL, or by content hash for notes) and either reject or
  update-in-place.
- **Tracing, not just structured logs.** Logs are structured and
  request-scoped (see `ARCHITECTURE.md`), but there's no distributed
  tracing connecting the stages of one request into a single trace view
  (e.g. OpenTelemetry) — would help a lot once latency debugging
  matters.
- **Health checks that actually check dependencies.** `/health`
  currently just confirms the process is up; it doesn't verify the
  database is reachable or the OpenAI API key is valid. A `/health/deep`
  variant would catch configuration issues before they surface as
  user-facing errors.

## Testing

- **Service-level tests beyond chunking.** Only `chunking.py` has unit
  tests today (chosen because it needs no API key). Add tests for
  `vector_store.py` (deterministic — no API calls needed) and mocked
  tests for `ingestion.py` / `rag.py` (the manual mocked run used to
  verify this build is a good starting point for a real test suite).
- **API-level integration tests** using `TestClient` with the OpenAI
  client mocked, covering the validation and error-mapping paths for
  each endpoint.
- **Live-integration test tier**, gated behind an env flag
  (`RUN_LIVE_TESTS=1`), that hits the real OpenAI API — useful in CI on
  a schedule, not on every commit, to catch real API/behavior drift
  without slowing down normal test runs.

## Frontend

- **Loading/error states for individual items**, not just the list as
  a whole (e.g. a spinner on the specific card being re-fetched).
- **Optimistic UI on ingest** — currently the new item only appears
  after the full fetch+embed round trip completes; showing a pending
  placeholder immediately would make saves feel instant.
- **Source click-through highlighting** — clicking a `[1]` citation in
  the answer text could scroll to / highlight the matching source card,
  rather than the two lists being visually separate.