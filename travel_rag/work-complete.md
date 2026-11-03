# Travel RAG: Progress checkpoint

Last verified: 2026-11-03

This file is the handoff for future chats: it records what is implemented and
tested, what is only planned, and the next learning step. The roadmap is in
`../.github/docs/plan.md`; the target design is in
`../.github/docs/ARCHITECTURE.md`.

## Current status

The project has a working FastAPI application shell. It does **not** yet have an
LLM endpoint or a RAG pipeline. Day 1 in the roadmap is in progress, not
complete.

## Work completed and verified

- Created the `travel_rag/` Python project with an isolated `.venv`.
- Created a FastAPI application in `app/main.py` and included its API router.
- Added `GET /`, which returns the plain-text response `server is running`.
- Added `GET /health`, which returns
  `{"status": "ok", "service": "travel-rag"}`.
- Added pytest coverage for both routes.
- Verified from `travel_rag/` with `./.venv/bin/python -m pytest -q`:
  **2 passed** (2026-11-03).
- Learned the initial request path: Uvicorn serves the FastAPI `app`; FastAPI
  matches the route decorator and invokes the handler; the handler response is
  sent back to the client. `TestClient` exercises these HTTP contracts without
  starting a separate server.

## Not implemented yet

- `POST /chat` and an LLM client, configuration, timeouts, and upstream-error
  handling.
- Document ingestion, chunking, embeddings, vector storage, retrieval, and
  grounded answers.
- Agent/tool flows, evaluation, and observability.

Ollama was previously noted as available in the local setup, but this
application does not call it. The embedding model and vector store have not
been selected or integrated.

## Next step

Continue the Day 1 learning milestone from `../.github/docs/plan.md`: implement
the first chat endpoint in a small step, explain the relevant FastAPI concepts
as we go, and test the success and failure paths with a fake client. Do not mark
Day 1 complete until its stated done criteria are met.

## Running and testing

From the `travel_rag/` directory:

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

In another terminal, from the same directory:

```bash
./.venv/bin/python -m pytest -q
```

Try `GET /`, `GET /health`, or the interactive API documentation at
`http://127.0.0.1:8000/docs`.

## Checkpoint maintenance

Update this file after a roadmap milestone or meaningful learning checkpoint
has been implemented and verified. Record the work, exact validation performed,
remaining gaps, and next step. Keep incomplete work explicitly marked as
in-progress; do not claim a feature is complete based only on a plan or an
unverified code change.
