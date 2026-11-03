# Travel RAG: Progress checkpoint

Last verified: 2026-11-03

This is the project handoff for future chats. It records verified work, current
gaps, and the next step. The priority roadmap is
`../.github/docs/14-day-interview-plan.md`; the target design is
`../.github/docs/ARCHITECTURE.md`.

## Current status

The FastAPI shell and the first chat endpoint are implemented. The Day 1 chat
step is working, but the full milestone is still in progress. There is no
document ingestion or RAG pipeline yet.

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

## Not implemented yet

- Document loading, chunking, embeddings, vector storage, and retrieval.
- Grounded `/ask` answers, citations, and retrieval evaluation.
- Tool calling, agent flows, human approval, and observability beyond the
  request ID and chat response metrics.

The local Ollama setup uses no API key; therefore, the plan's “bad API key”
experiment does not apply to this local integration. Upstream failures and
timeouts are covered through the fake-client tests.

## Next step

Begin the synthetic policy corpus and chunking work in the 14-day plan. Use
fictional policies, starting with Markdown so headings, tables, exceptions,
and policy identifiers are easy to inspect. Compare fixed-size-with-overlap
and structure-aware chunking, and test whether exceptions stay connected to
their governing rules. Keep the distinction clear: the current `/chat`
endpoint is not grounded RAG. Day 1 remains in progress until all applicable
roadmap criteria have been addressed.

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
