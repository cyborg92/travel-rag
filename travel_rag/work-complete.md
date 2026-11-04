# Travel RAG: Progress checkpoint

Last verified: 2026-11-04

This is the project handoff for future chats. It records verified work, current
gaps, and the next step. The priority roadmap is
`../.github/docs/14-day-interview-plan.md`; the target design is
`../.github/docs/ARCHITECTURE.md`.

## Current status

- **Day 1 (FastAPI + first LLM endpoint): complete.**
- **Day 2 (ingestion + chunking): in progress.** Four synthetic Markdown
  policies and a basic document loader are present. Chunking has not started.
- No embeddings, vector store, retrieval, or grounded RAG endpoint yet.

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

## Not implemented yet

- Chunking and chunk-level metadata.
- Embeddings, vector storage, and retrieval.
- Grounded `/ask` answers, citations, and retrieval evaluation.
- Tool calling, agent flows, human approval, and observability beyond the
  request ID and chat response metrics.

## Next step

Continue Day 2 by implementing a fixed-size-with-overlap chunker, then a
structure-aware chunker. Preserve the source filename on each chunk and test
how each strategy handles a rule and its exception. The current `/chat`
endpoint is not grounded RAG.

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
