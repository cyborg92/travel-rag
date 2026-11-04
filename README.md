# Travel RAG

A Python API project for a travel knowledge assistant. The current version
provides health routes, a chat endpoint backed by local Ollama, and an initial
utility for loading synthetic Markdown policies. The project is on Day 2:
document chunking is in progress; retrieval and grounded answers are not yet
implemented.

## Current features

- `GET /` returns the plain-text message `server is running`.
- `GET /health` returns `{"status": "ok", "service": "travel-rag"}`.
- `POST /chat` sends a question to Ollama and returns the answer, request ID,
  model-call latency, and token usage.
- Invalid chat requests return HTTP 422; upstream failures return HTTP 502;
  timeouts return HTTP 504. Errors include the request ID.
- FastAPI provides interactive API documentation at `/docs`.
- Four synthetic Markdown policies are in `travel_rag/data/policies/`.
- `app/utils/doc_reader.py` loads policies as sorted filename/text pairs.

## Technology

| Technology | Use |
|---|---|
| Python | Application language |
| FastAPI | HTTP API framework |
| Pydantic and pydantic-settings | API validation and environment-based settings |
| Uvicorn | Local ASGI server |
| httpx2 | Async HTTP client for Ollama |
| Ollama | Local chat model runtime (`llama3:8b` by default) |
| Pytest | Automated tests |

Dependencies are listed in [`travel_rag/requirements.txt`](travel_rag/requirements.txt).
No embedding model or vector database is integrated yet.

## Project layout

```text
.
├── README.md
├── .github/
│   └── docs/
│       ├── 14-day-interview-plan.md
│       ├── ARCHITECTURE.md
│       └── plan.md
└── travel_rag/
    ├── app/
    │   ├── api/
    │   │   └── routes.py       # Root, health, and chat endpoints
    │   ├── llm/
    │   │   └── client.py       # Async Ollama client and chat result types
    │   ├── utils/
    │   │   └── doc_reader.py   # Loads Markdown policy documents
    │   ├── config.py           # Ollama URL, model, and timeout settings
    │   ├── main.py             # FastAPI app, client lifecycle, request IDs
    │   └── schemas.py          # Chat request/response contracts
    ├── tests/
    │   ├── test_chat.py
    │   ├── test_doc_reader.py
    │   └── test_health.py
    ├── data/
    │   └── policies/           # Four synthetic Markdown policy documents
    ├── requirements.txt
    └── work-complete.md
```

The [14-day plan](.github/docs/14-day-interview-plan.md) is the priority
roadmap. The [architecture](.github/docs/ARCHITECTURE.md) describes the target
design, and [work-complete.md](travel_rag/work-complete.md) records verified
progress and the next step.

## Requirements

- Python 3.11 or newer
- `pip`
- [Ollama](https://ollama.com/) running locally with the configured model
  available

## Set up

Run these commands from the `travel_rag/` directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If you move the project, recreate `.venv` at its new location because virtual
environment scripts can refer to their original absolute path.

## Configure Ollama

Defaults:

| Environment variable | Default |
|---|---|
| `TRAVEL_RAG_OLLAMA_BASE_URL` | `http://127.0.0.1:11434` |
| `TRAVEL_RAG_OLLAMA_MODEL` | `llama3:8b` |
| `TRAVEL_RAG_OLLAMA_TIMEOUT_SECONDS` | `60` |

Set `TRAVEL_RAG_OLLAMA_MODEL` to a model tag installed in your Ollama setup if
you use a different model. The default local Ollama configuration does not
require an API key.

## Run the API

From `travel_rag/`, with the virtual environment activated:

```bash
uvicorn app.main:app --reload
```

Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) to try the API.
The OpenAPI schema is at
[http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json).

Example chat request:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"question":"Reply with the single word hello."}'
```

The response contains `answer`, `request_id`, `latency_ms`, and `token_usage`.
The same request ID is also returned in the `X-Request-ID` response header.

Stop the server with `Ctrl+C`.

## Run the tests

From `travel_rag/`:

```bash
python -m pytest -q
```

The tests use FastAPI's in-process `TestClient` and a fake chat client. They
cover route behavior, request validation, request IDs, timeouts, and upstream
failures without needing a running Ollama server.

## Request flow

1. Uvicorn serves the FastAPI application at `app.main:app`.
2. FastAPI middleware assigns a request ID. The app lifespan creates one shared
   async HTTP client for Ollama and closes it at shutdown.
3. FastAPI validates the JSON body as a `ChatRequest`.
4. The `/chat` handler calls the Ollama client, measures the call, and returns a
   typed `ChatResponse`; FastAPI serializes it as JSON.
5. Tests replace the Ollama client with a fake to verify API behavior
   deterministically.

## Planned direction

Day 1 (FastAPI and first LLM endpoint) is complete. Day 2 (ingestion and
chunking) is in progress: the synthetic corpus and basic loader are present,
and the loader test verifies four documents with non-empty text. Next is to
implement and compare chunking strategies. Embeddings, vector search, grounded
answers, evaluation, and tool/agent flows remain future milestones.
