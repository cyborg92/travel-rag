# Travel RAG

A hands-on learning project for building a travel-policy assistant with Python,
FastAPI, Ollama, and Chroma. All policy content is synthetic.

> **Project status:** The API, policy ingestion/chunking, Ollama embedding
> client, full-corpus Chroma indexing, and top-K semantic retrieval are
> implemented. `POST /ask` wires retrieval, labeled context, a grounding prompt,
> and chat together. Day 4 remains in progress while known/unknown questions
> and other roadmap behaviors are validated.

## What works today

| Area | Current behavior |
|---|---|
| `GET /` | Returns `server is running` as plain text. |
| `GET /health` | Returns a small JSON health response. |
| `POST /chat` | Sends a question to Ollama and returns the answer, request ID, latency, and token usage. |
| `POST /ask` | Retrieves up to three policy chunks, asks Ollama using labeled context, and returns the answer, mapped citations, all retrieved matches, and a refusal flag. |
| Policy utilities | Loads four synthetic Markdown policies and creates fixed-size or heading-based chunks. |
| Embeddings | Calls Ollama with the configured embedding model; a live call returned a 768-dimensional vector. |
| Chroma experiment | Indexes policy sections in a local persistent collection using stable IDs and `upsert`, then retrieves top-K matches. |
| `GET /chunkertest` | Displays policy section chunks for manual inspection. |

Chat validation errors return HTTP 422, Ollama timeouts return 504, and other
Ollama service errors return 502. These API paths are covered by automated
tests that use fakes rather than requiring a live Ollama service.
When retrieval returns no chunks, `/ask` returns an insufficient-evidence
response without calling the chat model. Citation labels in the answer are
mapped by retrieval order to Chroma IDs and metadata; the structured citations
do not trust metadata repeated by the model.

## How the pieces fit

```text
POST /chat ──> FastAPI ──> Ollama chat model

Synthetic policies ──> ingestion ──> Ollama embeddings ──> Chroma
POST /ask ──> Ollama embedding ──> top-K Chroma retrieval
         ──> labeled context + grounding prompt ──> Ollama chat model
```

`/chat` remains raw chat and does not use retrieved policy context. `/ask` uses
the retrieval flow for grounded answers.

## Quickstart

### Requirements

- Python 3.11 or newer
- [Ollama](https://ollama.com/) for live chat and embedding requests

### Install dependencies

From the repository root:

```bash
cd travel_rag
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If you move the project, recreate the virtual environment at its new location:
virtual-environment scripts can contain the path where the environment was
originally created.

### Prepare Ollama models

For the default configuration, make sure Ollama is running and has these
models:

```bash
ollama pull llama3:8b
ollama pull nomic-embed-text
```

The API can start without making a model request, but `/chat` and the embedding
experiment need Ollama and their respective models to be available.

### Start the API

From `travel_rag/` with the virtual environment activated:

```bash
uvicorn app.main:app --reload
```

- Interactive API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Health check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

Stop the server with `Ctrl+C`.

## Try the chat endpoint

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"question":"What does the policy say about cabin baggage?"}'
```

The JSON response contains `answer`, `request_id`, `latency_ms`, and
`token_usage`. The request ID is also returned in the `X-Request-ID` header.
Because this endpoint does not retrieve policy documents, its answer is not
grounded in the synthetic policy corpus.

## Configuration

Settings use the `TRAVEL_RAG_` environment-variable prefix.

| Variable | Default | Purpose |
|---|---|---|
| `TRAVEL_RAG_OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama server URL |
| `TRAVEL_RAG_OLLAMA_MODEL` | `llama3:8b` | Chat model |
| `TRAVEL_RAG_OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text` | Embedding model |
| `TRAVEL_RAG_OLLAMA_TIMEOUT_SECONDS` | `60` | Outbound Ollama request timeout |

For example, set `TRAVEL_RAG_OLLAMA_MODEL` to a model tag installed in your
Ollama setup to use a different chat model.

## Run the embedding and Chroma experiment

From `travel_rag/`:

```bash
python -m scripts.embedding_tester_script
```

The script loads and chunks all policy documents, embeds and upserts the
sections, embeds a sample question, and prints its top three matches with
metadata and distances. Re-running it uses the same IDs and updates existing
records rather than adding duplicates. Chroma persists its database in
`travel_rag/.chroma_db/`, which is ignored by Git.

The script is an experiment runner; reusable indexing and retrieval operations
live under `app/ingestion/` and `app/retrieval/`.

## Run the tests

From `travel_rag/`:

```bash
python -m pytest -q
```

The automated tests use fake clients for model calls, so they do not require a
running Ollama service.

## Roadmap

- **Complete:** FastAPI chat endpoint, synthetic policy loading/chunking, and
  Day 3 embedding/Chroma indexing and top-K retrieval experiment.
- **In progress:** Complete RAG: `POST /ask`, grounding instructions,
  insufficient-evidence behavior, and citation mapping are implemented.
  Validate known and unknown questions, contradictory evidence, and
  prompt-injection text as described in the roadmap.

See the [priority interview plan](.github/docs/14-day-interview-plan.md),
[target architecture](.github/docs/ARCHITECTURE.md),
[implementation decisions](.github/docs/decisions.md), and
[verified progress checkpoint](travel_rag/work-complete.md).
