# Travel RAG

A travel-policy assistant that answers questions from a policy corpus with
citations, and looks up and quotes bookings through tools the model can request
but never execute itself. Built with Python, FastAPI, Pydantic, Ollama and
Chroma. All airline, policy and booking data is synthetic.

The project focuses on the parts of an AI system that decide whether it can be
trusted: grounded answers and refusal, a labelled evaluation set that measures
retrieval, a tool-call trust boundary enforced in code, an agent loop with
limits the model cannot talk its way past, and a design for consequential
actions that require human confirmation.

## Highlights

- **Grounded answers with citations.** `POST /ask` retrieves policy sections,
  builds source-labelled context, and returns the answer with citations mapped
  back to the retrieved chunks. Empty retrieval returns an explicit
  insufficient-evidence response without calling the model. Whether the model
  declined is a schema-constrained `status` field, not a phrase match.
- **Measured retrieval.** A 14-case labelled dataset (paraphrase, multi-chunk,
  exact-code, contradictory, prompt-injection and unanswerable cases) with
  Hit@K, Precision@K, Recall@K and MRR. Semantic, BM25 and hybrid retrieval are
  compared on it.
- **Hybrid retrieval.** Semantic search and BM25 merged with Reciprocal Rank
  Fusion; on the eval set it recovered cases each method missed on its own.
- **A tool trust boundary.** The model only emits a tool request. Application
  code validates the arguments against a strict schema, authorizes the caller
  in the data layer, executes, and returns every failure as an observation the
  model can act on. Tool results expose only an allow-listed view of a booking.
- **A bounded agent loop.** The model can use tools over several rounds, under
  a call limit, a deadline and a duplicate-call guard enforced in code. Each
  run returns why it stopped.
- **Answer checks.** After the final reply, code appends any note or credit the
  tool results contain and the answer left out, and the confirmed figures of
  every successful quote, built from the tool result and not from the model.
- **Tested without a live model.** 352 pytest tests use fakes for the model,
  embeddings, HTTP calls and the clock.

## Architecture

```text
                 ┌──────────────────────── FastAPI ────────────────────────┐
  client ──────► │  /chat           raw model call                         │
                 │  /ask            RAG: embed → retrieve → context →      │
                 │                  model → cite                           │
                 │  /demo/tools/*   tool executor and quote, no model      │
                 └──────┬──────────────────────────────┬───────────────────┘
                        │                              │
          Ollama (chat, embeddings)          Chroma (policy chunks)

  Tool path:  model ──request──► executor ──validate──► authorize ──► mock backend
                     ◄─observation─┘   (Pydantic, extra=forbid)  (owner check)

  Agent loop (run from a script today, not behind an API route):
      model ⇄ tools, under: deadline · call limit · duplicate guard
      then: answer check (missing notes and credits, confirmed figures)
```

- Full design, request flows, failure modes and security model:
  [ARCHITECTURE.md](.github/docs/ARCHITECTURE.md)
- Decision records with evidence and trade-offs:
  [decisions.md](.github/docs/decisions.md)

## Status

| Capability | State |
|---|---|
| Chat endpoint with timeouts and error mapping (422 / 502 / 504) | Built |
| Request ID on every response (`X-Request-ID`) | Built |
| Policy ingestion: fixed-size and heading-aware chunking | Built |
| Embeddings, Chroma indexing, top-K semantic retrieval | Built |
| `POST /ask`: grounding prompt, citations, structured refusal status | Built |
| Evaluation dataset, retrieval metrics, and an end-to-end `/ask` runner | Built |
| BM25 and hybrid (RRF) retrieval, measured | Built; not yet wired into `/ask` |
| Tool registry, executor and trust boundary | Built |
| Tools: `get_booking`, `get_fare_rules`, `quote_change` | Built |
| System prompt for tool use | Built |
| Bounded agent loop (call limit, deadline, repeated-call guard, log lines) | Built; per-tool timeout designed |
| Recovery of a tool request the model wrote as text | Built (a reply that is entirely the request) |
| Answer check: missing notes and credits, confirmed figures | Built (a floor, not a correctness proof) |
| Demo routes for the deterministic tool paths | Built; no authentication |
| Demo route that runs the agent loop on a live model (`POST /demo/agent/run`) | Built; on by default, hide it with `TRAVEL_RAG_ENABLE_DEMO_AGENT=false`; one run at a time and a per-minute cap, no authentication |
| Agent loop behind an API route | Not built |
| Propose / confirm / execute for booking changes | In progress: proposal model, state machine and SQLite store built; atomic claim, confirm and execute not yet |
| Authentication | Not built; a fixed test user stands in |
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

End to end through `POST /ask` (`llama3.1:8b`, one run per case, results in
`travel_rag/eval/results/`): the refusal decision was correct on 12 of 14
cases with a phrase-matched refusal and 14 of 14 after moving to a
schema-constrained `status`. Answer quality got terser under the constraint and
one answer misapplied a rule. These are single runs, so some of the difference
may be sampling noise.

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
- **The model sees an allow-listed view.** `get_booking` returns a model that
  declares the fields the model may see, so the owner identifier is not
  included and a field added to a booking later does not reach the model
  unless the view lists it.
- **`quote_change` only quotes.** Changing a booking is reserved for the
  propose / confirm / execute flow, where a person confirms a stored proposal.

Observed against a local model, the validation layer caught invented arguments
(`your_booking_reference`, `new_date: "YYYY-MM-DD"`) and the model recovered
from the error message. The final answer can still drift from the tool result
(currency, omitted credits or notes, a wrong total); the loop appends the
missing notes and credits and the confirmed figures from the tool result, but
cannot make the model's own wording correct.
[decisions.md](.github/docs/decisions.md) records what fixed what and what
remains open.

## The agent loop

```text
ask the model
while the reply asks for tools:
    if the deadline has passed:            stop ("timeout")
    for each requested call:
        if the call limit is reached:      stop ("too_many_calls")
        if the same call already ran:      tell the model, skip it
        else:                              run it through the executor, record it
    ask the model again
answer ("answered"), then append missing notes and credits and the confirmed figures
```

- The model function and the clock are passed in, so tests force every stop
  reason with a scripted fake model and a stepping clock: no Ollama, no waiting.
- A model that only repeats itself never reaches the call limit, because
  skipped duplicates do not count; the deadline stops it.
- A reply that is entirely a JSON request naming a registered tool is treated
  as a request and goes through the same validation and guards.
- It is run from `scripts/ollama_tools_agent_experiment_script.py`; it is not
  behind an API route yet.

## Project layout

```text
.
├── README.md
├── .github/docs/            ARCHITECTURE.md, decisions.md
└── travel_rag/
    ├── app/
    │   ├── main.py          app, shared Ollama client, request-ID middleware, 422 handler
    │   ├── config.py        settings (TRAVEL_RAG_ prefix)
    │   ├── schemas.py       request and response models
    │   ├── api/routes/      operations (/, /health, /chunkertest), chat (/chat, /ask), demo (/demo/*)
    │   ├── llm/             async Ollama chat client, plain and schema-constrained
    │   ├── embeddings/      Ollama embedding client
    │   ├── ingestion/       document loading, chunking, indexing
    │   ├── vector_store/    Chroma access (persists to travel_rag/.chroma_db)
    │   ├── retrieval/       semantic retrieval, BM25, RRF fusion, metrics
    │   ├── rag/             context builder, grounding prompt, citation mapping
    │   ├── tools/           registry, argument schemas, executor, result views
    │   ├── mock_backend/    synthetic bookings and fares
    │   ├── agent/           system prompt, state, loop, model function,
    │   │                    answer check, text-request recovery
    │   └── proposals/       proposal model, state transitions, SQLite store (in progress)
    ├── data/policies/       synthetic policy documents
    ├── eval/
    │   ├── datasets/        labelled retrieval dataset (JSONL)
    │   └── results/         saved /ask runs
    ├── scripts/             experiment and evaluation runners
    ├── tests/               pytest suite
    └── requirements.txt
```

## Quickstart

Requirements: [Ollama](https://ollama.com/) for live chat and embeddings, and
Python 3 with `venv`. Developed and tested on Python 3.14; other versions are
not verified.

```bash
cd travel_rag
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

ollama pull llama3.1:8b
ollama pull nomic-embed-text

# Build the policy index once (writes travel_rag/.chroma_db); /ask needs it
python -m scripts.embedding_tester_script

uvicorn app.main:app --reload
```

Interactive API docs are at <http://127.0.0.1:8000/docs>. Without the index,
`/ask` returns the insufficient-evidence response.

### Endpoints

| Route | Purpose |
|---|---|
| `GET /` | Plain-text "server is running" |
| `GET /health` | Health check |
| `POST /chat` | Raw model call: answer, request ID, latency, token usage |
| `POST /ask` | Grounded answer with citations, retrieved chunks and a refusal flag |
| `GET /chunkertest` | Shows the section chunks, for inspecting the chunker |
| `POST /demo/tools/execute` | Send a tool request as a model would and see the observation (see below) |
| `POST /demo/tools/quote` | Quote a date change, with an optional fixed `now` (see below) |

Every response carries an `X-Request-ID` header. Request validation errors
return 422 with the request ID in the body; model and embedding failures map to
504 (timeout) and 502 (service error).

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Must my personal item fit under the seat?"}'
```

### Demo routes

The two `/demo` routes run the deterministic code paths with no model, so they
work without Ollama. The caller is always the fixed synthetic user `user-1`;
identity is never read from the request. There is **no authentication** on
them, so turn them off before exposing the server beyond people you trust:
set `TRAVEL_RAG_ENABLE_DEMO_ROUTES=false` and they are not mounted.

```bash
# PNR004 belongs to another user and PNR999 does not exist: the same message
curl -X POST http://127.0.0.1:8000/demo/tools/execute \
  -H 'Content-Type: application/json' \
  -d '{"name":"get_booking","arguments":{"reference":"PNR004"}}'

# A quote at a fixed "now", so the fee band is reproducible
curl -X POST http://127.0.0.1:8000/demo/tools/quote \
  -H 'Content-Type: application/json' \
  -d '{"reference":"PNR001","new_date":"2026-12-12","now":"2026-11-12T10:00:00"}'
```

An extra `user_id` argument is rejected by validation, as it would be for a
model.

### Configuration

Settings use the `TRAVEL_RAG_` environment-variable prefix.

| Variable | Default | Purpose |
|---|---|---|
| `TRAVEL_RAG_OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama server URL |
| `TRAVEL_RAG_OLLAMA_MODEL` | `llama3.1:8b` | Chat model |
| `TRAVEL_RAG_OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text` | Embedding model |
| `TRAVEL_RAG_OLLAMA_TIMEOUT_SECONDS` | `60` | Outbound Ollama request timeout |
| `TRAVEL_RAG_ENABLE_DEMO_ROUTES` | `true` | Mount the `/demo` routes |

### Experiments

From `travel_rag/`, in the activated environment. Ollama is needed where noted.

```bash
python -m scripts.embedding_tester_script             # index the corpus into Chroma and query it (Ollama)
python -m scripts.retriever_metrics_tester_script     # semantic retrieval metrics on the eval set (Ollama)
python -m scripts.bm25_tester_script                  # BM25 over the corpus, three tokenizer patterns
python -m scripts.bm25_metrics_tester_script          # BM25 retrieval metrics on the eval set
python -m scripts.hybrid_metrics_tester_script        # semantic vs BM25 vs hybrid (Ollama)
python -m scripts.ask_endpoint_tester_script          # every eval case through a running /ask; saves JSONL (server + Ollama)
python -m scripts.ollama_tools_experiment_script      # one tool-calling round trip, printing every message (Ollama)
python -m scripts.ollama_tools_agent_experiment_script # the agent loop against a local model (Ollama)
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
