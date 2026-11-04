# Travel RAG: Progress checkpoint

Last verified: 2026-11-05

This is the project handoff for future chats. It records verified work, current
gaps, and the next step. The priority roadmap is
`../.github/docs/14-day-interview-plan.md`; the target design is
`../.github/docs/ARCHITECTURE.md`.

## Current status

- **Day 1 (FastAPI + first LLM endpoint): complete.**
- **Day 2 (ingestion + chunking): complete.** Four synthetic policies are
  loaded and chunked with fixed-size/overlap and heading-based strategies.
  Chunk records carry source, zero-based index, text, and section when
  structure-aware chunking is used.
- **Day 3 (embeddings + vector store): in progress.** The Ollama embedding
  client is configured for `nomic-embed-text`, passed fake-HTTP tests, and
  returned a 768-dimensional vector in a live call. Chroma indexing and
  semantic retrieval remain.

## Work completed and verified

- Created the `travel_rag/` Python project with an isolated `.venv`.
- Created the FastAPI application and registered its API router.
- Added `GET /`, returning plain text `server is running`.
- Added `GET /health`, returning `{"status": "ok", "service": "travel-rag"}`.
- Added `POST /chat` with a Pydantic request model. It rejects missing, blank,
  overlong, and extra fields with HTTP 422.
- Configured the default Ollama URL, model (`llama3:8b`), and timeout through
  `pydantic-settings`; these can be overridden with `TRAVEL_RAG_OLLAMA_*`
  environment variables.
- Added an async Ollama client using the existing `httpx2` dependency. One
  shared HTTP client is created and closed in FastAPI's lifespan.
- Chat success responses include the answer, request ID, model-call latency,
  and prompt/completion token counts. The ID is also returned in the
  `X-Request-ID` header.
- Validation errors return 422, Ollama timeouts return 504, and other Ollama
  failures return 502. Error bodies include the request ID.
- Added deterministic chat tests using a fake client for success, validation,
  timeout, and upstream-error cases.
- Verified with `cd travel_rag && ./.venv/bin/python -m pytest -q`:
  **10 passed**.
- Completed the Day 1 experiments: manually called `POST /chat` through
  FastAPI `/docs` against local Ollama and observed raw-chat behavior for the
  fictional `covid-travel-tax` question. The local Ollama setup does not use an
  API key, so the bad-key experiment does not apply. Timeout and upstream
  failures were covered with the fake chat client.
- Verified a real request through Uvicorn and local Ollama using `curl`. The
  model returned `Hello`; the response included request ID
  `23d8c88b-9981-4336-86e3-9c966dcfb13a`, latency, and token counts.
- Manually tested `POST /chat` through FastAPI's interactive `/docs`; the
  request succeeded.
- Ran an unsupported-claim experiment: asked about a made-up
  `covid-travel-tax` in the context of generic IndiGo travel policy. The model
  responded with general COVID-related airline-policy information instead of
  saying it did not know what the invented charge was. This was an observation
  from raw chat, not a verified claim about any airline's actual policy.
- Learned that FastAPI lifespan owns resources shared across requests, while
  dependency injection lets tests substitute a fake chat client. Pydantic
  validates the incoming request before the route handler runs.
- Created four synthetic Markdown documents: ticket change, cancellation,
  baggage, and disruption policies.
- Added `app/utils/doc_reader.py` to load sorted Markdown files as
  `(filename, text)` pairs.
- Added `tests/test_doc_reader.py` to verify the four expected filenames and
  non-empty text for every policy.
- Verified the complete test suite with
  `cd travel_rag && ./.venv/bin/python -m pytest -q`: **11 passed** on
  2026-11-04.
- Added `app/utils/chunker.py` with fixed-size character chunks and configurable
  overlap. The loop stops after the final chunk, avoiding a redundant trailing
  chunk when the previous chunk already reached the end of the text.
- Added `tests/test_chunker.py` for overlap boundaries, empty and short text,
  final partial chunks, and invalid chunk size/overlap values.
- Verified `cd travel_rag && ./.venv/bin/python -m pytest tests/test_chunker.py -q`:
  **9 passed**; full suite `cd travel_rag && ./.venv/bin/python -m pytest -q`:
  **20 passed** on 2026-11-04.
- Updated both chunkers to return dictionary records with `source`,
  zero-based `chunk_index`, and `chunk`; section-based chunks also include a
  `section` heading. The fixed-size chunker uses character counts and overlap;
  section-based splitting keeps each `##` section together.
- Ran the chunking comparison on the synthetic baggage policy. With
  `chunk_size=400, overlap=0`, fixed-size chunk 1 ended in the middle of
  `### Cabin-baggage exceptions` and chunk 2 began with the remainder, apart
  from the cabin allowance table. The structure-aware chunk kept the table,
  heading, and exception rules together in section 2. This is the concrete
  example of chunk boundaries changing which context is available.
- Added chunk-index assertions to the chunker tests. Verified
  `cd travel_rag && ./.venv/bin/python -m pytest -q`: **21 passed** and
  `git diff --check` passed on 2026-11-04.
- Added `app/embeddings/client.py`, which sends text to Ollama's `/api/embed`
  endpoint and returns a vector. It maps timeout and service/response failures
  explicitly, rejects blank input and invalid vectors, and reuses the shared
  async HTTP client from the application lifespan.
- Updated the checkpoint and project/architecture roadmaps to mark Day 2
  complete and Day 3 in progress. Added `.github/docs/decisions.md` to record
  the initial embedding-model choice and its trade-offs.
- Selected `nomic-embed-text` as the local baseline embedding model and added
  `TRAVEL_RAG_OLLAMA_EMBEDDING_MODEL` configuration. The choice and trade-offs
  are recorded in `.github/docs/decisions.md`.
- Added fake-HTTP tests for successful embeddings, timeouts, upstream and
  malformed responses, empty vectors, and blank input. Verified
  `cd travel_rag && ./.venv/bin/python -m pytest tests/test_embeddings.py -q`:
  **7 passed**; full suite `cd travel_rag && ./.venv/bin/python -m pytest -q`:
  **28 passed** on 2026-11-04.
- On 2026-11-05, the user ran the Python embedding client against local Ollama
  with `nomic-embed-text`. It returned a 768-dimensional vector; the first
  five values were `[-0.037546925, 0.079259604, -0.1783307, -0.002847416,
  0.010480644]`. This verifies a live embedding request, not retrieval quality.

## Not implemented yet

- Chroma indexing and semantic retrieval.
- Grounded `/ask` answers, citations, and retrieval evaluation.
- Tool calling, agent flows, human approval, and observability beyond the
  request ID and chat response metrics.

## Next step

Continue Day 3 by comparing embeddings for one policy-relevant query, a
matching chunk, and an unrelated chunk using cosine similarity. Then add Chroma
indexing with stable IDs so rerunning ingestion updates rather than duplicates
chunks, and implement semantic top-K retrieval. The current `/chat` endpoint
is not grounded RAG.

## Run and test

From the `travel_rag/` directory:

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

In another terminal:

```bash
./.venv/bin/python -m pytest -q
```

Use `/docs` to inspect and call the API. Ollama must be running with the
configured model available for real `/chat` requests; automated tests use a
fake and do not require Ollama.

## Checkpoint maintenance

After each meaningful milestone, update this file with the implemented work,
the exact validation run and result, remaining gaps, and next step. Only record
work as complete after it has been verified; keep partial milestones marked
in progress.
