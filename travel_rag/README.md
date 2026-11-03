# Travel RAG learning project

We are building this in small, testable milestones. This first checkpoint sets up
the API shell; it does not yet load documents, call Ollama, or perform retrieval.

## Project structure

```text
travel_rag/
├── app/
│   ├── api/
│   │   └── routes.py       # HTTP endpoints and response schemas
│   └── main.py             # Creates the FastAPI application
├── tests/
│   └── test_health.py      # API behavior checks
├── requirements.txt        # Python packages for this checkpoint
└── README.md
```

As the pipeline grows, we will add focused modules for configuration, document
ingestion, retrieval, answer generation, and later the agent/tools. They are
intentionally not empty placeholders yet.

## Set up the environment

Run these commands from this directory. The virtual environment keeps this
project's packages separate from the other labs.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Run the API

```bash
uvicorn app.main:app --reload
```

- `GET http://127.0.0.1:8000/health` is a simple liveness check.
- `http://127.0.0.1:8000/docs` is FastAPI's interactive API documentation.
- `http://127.0.0.1:8000/openapi.json` is the machine-readable API contract.

## Run the test

```bash
python -m pytest
```

## What happens on a request?

1. Uvicorn accepts the HTTP request and runs the ASGI application.
2. FastAPI matches `/health` to `health_check` in `app/api/routes.py`.
3. The handler returns a `HealthResponse`; FastAPI validates and serializes it
   as JSON.
4. The test uses FastAPI's in-process `TestClient`, so it checks the HTTP
   contract without starting a separate server.

Next, we will define a small travel-document corpus and build the ingestion
path. Ollama is installed locally, but we will choose and verify an embedding
model before indexing anything.
