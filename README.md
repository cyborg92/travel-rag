# Travel RAG

A Python API project for a travel knowledge assistant. The project is being
built incrementally: the current version is a small FastAPI application with
two operational endpoints. Document ingestion, retrieval, LLM answers, and
agent tools are planned, but are not implemented yet.

## Current features

- `GET /` returns the plain-text message `server is running`.
- `GET /health` returns a JSON health response:

  ```json
  {
    "status": "ok",
    "service": "travel-rag"
  }
  ```

- FastAPI provides interactive API documentation at `/docs`.
- Pytest and FastAPI's `TestClient` cover both routes.

## Technology

| Technology | Use |
|---|---|
| Python | Application language |
| FastAPI | HTTP API framework |
| Pydantic | API response validation and serialization |
| Uvicorn | Local ASGI server |
| Pytest | Automated tests |

The dependencies currently used by the app are listed in
[`travel_rag/requirements.txt`](travel_rag/requirements.txt). An LLM integration,
embedding model, and vector database have not been added yet.

## Project layout

```text
.
├── README.md
├── .github/
│   └── docs/
│       ├── ARCHITECTURE.md
│       └── plan.md
└── travel_rag/
    ├── app/
    │   ├── api/
    │   │   └── routes.py   # Root and health routes and health response model
    │   └── main.py         # Creates the FastAPI app and registers the router
    ├── tests/
    │   └── test_health.py  # HTTP contract tests for the routes
    ├── requirements.txt
    └── work-complete.md
```

The project roadmap and target design are maintained in the repository's
[implementation plan](.github/docs/plan.md) and
[architecture document](.github/docs/ARCHITECTURE.md). The current verified
work and next step are tracked in
[work-complete.md](travel_rag/work-complete.md).

## Requirements

- Python 3.11 or newer
- `pip`

## Set up a local environment

Run the commands from this directory (`travel_rag/`):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

If you move this project to a different directory, recreate `.venv` at its new
location. Virtual environments can contain scripts that refer to the original
absolute path.

## Run the API

From `travel_rag/`, with the virtual environment activated:

```bash
uvicorn app.main:app --reload
```

Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) to try the
endpoints interactively. The OpenAPI schema is available at
[http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json).

You can also check the routes from a terminal:

```bash
curl http://127.0.0.1:8000/
curl http://127.0.0.1:8000/health
```

Expected responses:

```text
server is running
```

```json
{"status":"ok","service":"travel-rag"}
```

Stop the development server with `Ctrl+C`.

## Run the tests

From `travel_rag/`:

```bash
python -m pytest -q
```

The tests use FastAPI's in-process `TestClient`; they do not require a separate
Uvicorn server. They check the HTTP status and response body for each route.

## Request flow

1. Uvicorn serves the FastAPI application specified by `app.main:app`.
2. `app/main.py` creates the app and includes the router from
   `app/api/routes.py`.
3. FastAPI matches the requested path and method to a route handler.
4. The handler returns a response. FastAPI serializes the health response as
   JSON; the root route explicitly returns plain text.
5. Tests make requests directly to the app and verify the resulting HTTP
   contract.

## Planned direction

The roadmap builds toward a travel-document question-answering API:

1. Add a chat/model client and validated API input.
2. Load synthetic travel documents, split them into chunks, and attach source
   metadata.
3. Embed and index the chunks, then implement retrieval.
4. Generate answers grounded in retrieved documents and return citations.
5. Add retrieval evaluation and, later, narrowly scoped tools and agent flows.

These are planned milestones, not current features. Consult the
[implementation plan](.github/docs/plan.md) for their order and the
[architecture document](.github/docs/ARCHITECTURE.md) for the target design.
