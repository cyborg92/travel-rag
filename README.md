# Travel RAG

A travel-policy assistant that answers questions from a policy corpus with
citations, and looks up and quotes bookings through tools the model can request
but never execute itself. Built with Python, FastAPI, Pydantic, Ollama and
Chroma. All airline, policy and booking data is synthetic.

The project focuses on the parts of an AI system that decide whether it can be
trusted: grounded answers and refusal, a labelled evaluation set that measures
retrieval, a tool-call trust boundary enforced in code, and a design for
consequential actions that require human confirmation.

## Highlights

- **Grounded answers with citations.** `POST /ask` retrieves policy sections,
  builds source-labelled context, and returns the answer with citations mapped
  back to the retrieved chunks. Empty retrieval returns an explicit
  insufficient-evidence response without calling the model.
- **Measured retrieval.** A 14-case labelled dataset (paraphrase, multi-chunk,
  exact-code, contradictory, prompt-injection and unanswerable cases) with
  Hit@K, Precision@K, Recall@K and MRR. Semantic, BM25 and hybrid retrieval are
  compared on it.
- **Hybrid retrieval.** Semantic search and BM25 merged with Reciprocal Rank
  Fusion; on the eval set it recovered cases each method missed on its own.
- **A tool trust boundary.** The model only emits a tool request. Application
  code validates the arguments against a strict schema, authorizes the caller
  in the data layer, executes, and returns every failure as an observation the
  model can act on.
- **Tested without a live model.** 264 pytest tests use fakes for the model,
  embeddings, HTTP calls and the clock.

## Architecture

```text
                 ┌──────────────────────── FastAPI ────────────────────────┐
  client ──────► │  /chat  raw model call                                  │
                 │  /ask   RAG: embed → retrieve → context → model → cite  │
                 └──────┬──────────────────────────────┬───────────────────┘
                        │                              │
          Ollama (chat, embeddings)          Chroma (policy chunks)

  Tool path:  model ──request──► executor ──validate──► authorize ──► mock backend
                     ◄─observation─┘   (Pydantic, extra=forbid)  (owner check)
```

- Full design, request flows, failure modes and security model:
  [ARCHITECTURE.md](.github/docs/ARCHITECTURE.md)
- Decision records with evidence and trade-offs:
  [decisions.md](.github/docs/decisions.md)

## Status

| Capability | State |
|---|---|
| Chat endpoint with timeouts and error mapping (422 / 502 / 504) | Built |
| Policy ingestion: fixed-size and heading-aware chunking | Built |
| Embeddings, Chroma indexing, top-K semantic retrieval | Built |
| `POST /ask`: grounding prompt, citations, refusal signal | Built |
| Evaluation dataset and retrieval metrics | Built |
| BM25 and hybrid (RRF) retrieval, measured | Built; not yet wired into `/ask` |
| Tool registry, executor and trust boundary | Built |
| Tools: `get_booking`, `get_fare_rules`, `quote_change` | Built |
| System prompt for tool use | Built |
| Bounded agent loop (call limit, deadline, repeated-call guard, trace log) | Built; per-tool timeout designed |
| Answer check: required notes and credits, plus code-built confirmed figures | Built (a floor, not a correctness proof) |
| Propose / confirm / execute for booking changes | Designed |
| Tracing, metrics, audit log | Designed |

## Evaluation results

Retrieval at top 3 on the 12 answerable cases of the 14-case set:

| Strategy | Hit@3 | Precision@3 | Recall@3 | MRR |
|---|---|---|---|---|
| Semantic | 1.000 | 0.333 | 0.833 | 0.847 |
| BM25 | 0.917 | 0.333 | 0.792 | 0.833 |
| Hybrid (RRF, k=60) | 1.000 | 0.361 | 0.875 | 0.861 |

BM25 found a literal-wording case that semantic search missed, semantic search
found a paraphrase BM25 missed entirely, and fusion recovered both. The
difference is one or two cases on a small set, and multi-chunk questions are
not improved by any strategy, so this is a direction, not a benchmark.

## The tool trust boundary

```text
model sends     {"name": "quote_change", "arguments": {"reference": "PNR001", "new_date": "2026-11-21"}}
executor        unknown tool?        → "Unknown tool ..."
                schema invalid?      → "Invalid arguments ..."   (extra keys, bad date, wrong format)
                run with user_id     → identity comes from application code, never from the model
data layer      not found / not owner → same "No booking found" message for both
                unexpected error      → generic message to the model, full error to the log
returns         a Pydantic result serialized as JSON, e.g. fee, fare difference, credit, total, currency
```

- **Identity is not a tool argument.** The argument models use
  `extra="forbid"`, so a model-supplied `user_id` is rejected.
- **"Missing" and "not yours" look identical,** so the model cannot be used to
  probe which booking references exist.
- **`quote_change` only quotes.** Changing a booking is reserved for the
  propose / confirm / execute flow, where a person confirms a stored proposal.

Observed against a local model, the validation layer caught invented arguments
(`your_booking_reference`, `new_date: "YYYY-MM-DD"`) and the model recovered
from the error message. The final answer can still drift from the tool result
(currency, omitted credits or notes, a wrong total); the loop now appends the
missing notes and credits and the confirmed figures from the tool result, but
cannot make the model's own wording correct; [decisions.md](.github/docs/decisions.md)
records what fixed what and what remains open.

## Project layout

```text
travel_rag/
├── app/
│   ├── api/routes/      FastAPI routes (operations, chat, ask)
│   ├── llm/             async Ollama chat client
│   ├── embeddings/      Ollama embedding client
│   ├── ingestion/       document loading, chunking, indexing
│   ├── vector_store/    Chroma access
│   ├── retrieval/       semantic retrieval, BM25, RRF fusion, metrics
│   ├── rag/             context builder, grounding prompt, citation mapping
│   ├── tools/           tool registry, argument schemas, executor
│   ├── mock_backend/    synthetic bookings and fares
│   └── agent/           system prompt, agent state, bounded agent loop, model function
├── data/policies/       synthetic policy documents
├── eval/datasets/       labelled retrieval dataset (JSONL)
├── scripts/             experiment runners (metrics, hybrid comparison, tools)
└── tests/               pytest suite
```

## Quickstart

Requirements: Python 3.11 or newer, and [Ollama](https://ollama.com/) for live
chat and embeddings.

```bash
cd travel_rag
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

ollama pull llama3.1:8b
ollama pull nomic-embed-text

uvicorn app.main:app --reload
```

Once the app is running, interactive API docs are at <http://127.0.0.1:8000/docs>.

### Endpoints

| Route | Purpose |
|---|---|
| `GET /health` | Health check |
| `POST /chat` | Raw model call: answer, request ID, latency, token usage |
| `POST /ask` | Grounded answer with citations, retrieved chunks and a refusal flag |
| `GET /chunkertest` | Shows the section chunks, for inspecting the chunker |

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Must my personal item fit under the seat?"}'
```

### Configuration

Settings use the `TRAVEL_RAG_` environment-variable prefix.

| Variable | Default | Purpose |
|---|---|---|
| `TRAVEL_RAG_OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama server URL |
| `TRAVEL_RAG_OLLAMA_MODEL` | `llama3.1:8b` | Chat model |
| `TRAVEL_RAG_OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text` | Embedding model |
| `TRAVEL_RAG_OLLAMA_TIMEOUT_SECONDS` | `60` | Outbound Ollama request timeout |

### Experiments

From `travel_rag/`, with Ollama running:

```bash
python -m scripts.embedding_tester_script        # index the corpus into Chroma and query it
python -m scripts.retriever_metrics_tester_script # semantic retrieval metrics on the eval set
python -m scripts.hybrid_metrics_tester_script    # semantic vs BM25 vs hybrid
python -m scripts.ollama_tools_experiment_script  # a tool-calling round trip, printing every message
python -m scripts.ollama_tools_agent_experiment_script  # the agent loop against a local model
```

### Tests

```bash
cd travel_rag
python -m pytest -q
```

The suite does not need Ollama or a network connection.

## Data

Every policy, booking, fare and passenger in this repository is fictional. One
policy document deliberately contains an embedded instruction, to test how the
system handles prompt injection from retrieved content.
