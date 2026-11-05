# Travel RAG

A hands-on learning project for building a travel-policy assistant with Python,
FastAPI, Ollama, and Chroma. All policy content is synthetic.

> **Project status:** The API, document loading and chunking, Ollama embedding
> client, and a single-chunk Chroma storage experiment are implemented. Bulk
> indexing and semantic retrieval are the next steps. The current `/chat`
> endpoint is raw chat, not a grounded RAG endpoint.

## What works today

| Area | Current behavior |
|---|---|
| `GET /` | Returns `server is running` as plain text. |
| `GET /health` | Returns a small JSON health response. |
| `POST /chat` | Sends a question to Ollama and returns the answer, request ID, latency, and token usage. |
| Policy utilities | Loads four synthetic Markdown policies and creates fixed-size or heading-based chunks. |
| Embeddings | Calls Ollama with the configured embedding model; a live call returned a 768-dimensional vector. |
| Chroma experiment | Stores and reads back one chunk in a local persistent collection using `upsert`. |
| `GET /chunkertest` | Displays policy section chunks for manual inspection. |

Chat validation errors return HTTP 422, Ollama timeouts return 504, and other
Ollama service errors return 502. These API paths are covered by automated
tests that use fakes rather than requiring a live Ollama service.

## How the pieces fit

```text
POST /chat ──> FastAPI ──> Ollama chat model

Synthetic policies ──> load and chunk ──> Ollama embeddings ──> Chroma
                                                               (experiment)
```

The second flow currently demonstrates storing one selected chunk. It does
not yet index all policies or search Chroma for relevant chunks.

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
./.venv/bin/python -m app.utils.embedding_tester_script
```

The script embeds a selected policy section and a question, compares their
vectors, stores the section in the local Chroma collection, and reads it back.
The Chroma database is written to `travel_rag/.chroma_db/`, which is ignored by
Git. This is a learning experiment, not yet a full-corpus ingestion or
retrieval command.

## Run the tests

From `travel_rag/`:

```bash
python -m pytest -q
```

The automated tests use fake clients for model calls, so they do not require a
running Ollama service.

## Roadmap

- **Complete:** FastAPI chat endpoint and synthetic policy loading/chunking.
- **In progress:** Embeddings and vector storage.
- **Next:** Index all policy sections, retrieve top-K matches from Chroma, then
  build a grounded answer flow with citations.

See the [priority interview plan](.github/docs/14-day-interview-plan.md),
[target architecture](.github/docs/ARCHITECTURE.md),
[implementation decisions](.github/docs/decisions.md), and
[verified progress checkpoint](travel_rag/work-complete.md).
