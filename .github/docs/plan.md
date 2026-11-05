# TravelAssist AI: 14-Day Build-and-Defend Plan

> Owner: Rachit Handa (SDE-4 / G10, enterprise application engineer expanding into AI application engineering)
> Goal: Personally build ONE end-to-end AI application, then defend every architectural decision in an SDE-4 interview.
> All data is synthetic. Nothing here is real production or passenger data.

---

## 0. Ground rules

**Philosophy:** Build first, learn concepts when the build demands them.

```
Problem -> Implement -> Run -> Something fails -> Understand why -> Debug -> Improve -> Deep concept understanding
```

**Time split:** ~70% hands-on coding, ~20% design/debugging, ~10% interview prep.

**Daily rhythm (target 2-3 hours on weekdays, more on weekends):**

| Block | Share | Activity |
|---|---|---|
| Build | 60-70% | Implement the day's smallest working version |
| Break | 15-20% | Run the failure experiments, record observations |
| Defend | 10-15% | Answer the day's interview questions out loud, write answers in `interview-notes.md` |

**Hard rules**
1. No LangChain/LangGraph until Day 9 is complete and I can explain what they abstract.
2. Every day ends with something runnable and committed.
3. Every day has "break it on purpose" experiments. Record what I predicted vs. what happened.
4. Every design choice gets a one-paragraph entry in `decisions.md` in this docs folder (what, why, alternatives, trade-off).
5. Always be able to answer: "Why does this need an agent?"
6. Be honest in the interview. Positioning: *SDE-4 production/architecture maturity + rapidly developing hands-on AI implementation skill.*

** compliance ( AI usage guidelines)**
- Corporate account and managed device only. Use an LLM endpoint and key approved by the organization.
- No secrets in code, config, examples, or git history. Local dev uses a git-ignored `.env`; real environments use AWS Secrets Manager / Azure Key Vault.
- Synthetic data only. Never paste real PNRs, passenger names, payment data, or internal documents into prompts, logs, fixtures, or notebooks.
- All AI-generated code is reviewed and validated by me before commit.
- Deployments only via Azure DevOps / GitHub Actions. No ad hoc deploy scripts.
- PRs reference a ticket ID (Jira/ServiceNow). If none exists, ask; never invent one. Production changes need a rollback plan.
- Out of scope: flight-critical, safety-critical, maintenance or regulatory systems.

---

## 1. Target architecture (end state)

```
User / (optional Angular UI)
        |
        v
FastAPI  (validation, auth stub, request_id, logging)
        |
        v
Orchestration layer (deterministic workflow first, agent where justified)
        |
   +----+-----------------------------+
   |                                  |
   v                                  v
Knowledge / RAG                  Tools / Agent loop
 ingest -> chunk -> embed         get_booking
 vector DB + BM25                 get_fare_rules
 hybrid retrieval                 calculate_change_options
 rerank                           create_change_request (HITL, idempotent)
 context builder
   |                                  |
   +----------------+-----------------+
                    v
                   LLM
                    v
          Grounded response + citations
                    v
     Evaluation  /  Observability  /  Audit log
```

See `ARCHITECTURE.md` in this docs folder for details.

---

## 2. Target repository layout (grows incrementally; do not pre-create)

```
travel-rag/
├── .github/
│   ├── copilot-instructions.md
│   └── docs/
│       ├── ARCHITECTURE.md
│       ├── decisions.md
│       ├── interview-notes.md
│       └── plan.md
└── travel_rag/
    ├── app/
    │   ├── main.py              # FastAPI app, routes
    │   ├── config.py            # typed settings (only place that reads env)
    │   ├── schemas.py           # Pydantic API contracts
    │   ├── llm/                 # LLM client wrapper, timeouts
    │   ├── rag/                 # ingest, chunk, embed, store, retrieve, rerank, context
    │   ├── agent/               # tool registry, tool schemas, loop, state
    │   ├── tools/               # get_booking, get_fare_rules, ...
    │   ├── mock_backend/        # synthetic booking + fare data
    │   └── observability/       # logging, trace records, metrics
    ├── data/
    │   └── policies/            # synthetic policy docs (markdown)
    ├── eval/
    │   ├── datasets/            # retrieval + generation + agent scenarios (JSONL)
    │   └── run_eval.py
    ├── tests/
    ├── .env.example
    └── requirements.txt
```

Paths such as `app/`, `data/`, `eval/`, and `tests/` in the milestones are relative to `travel_rag/`.

---

## 3. Progress tracker

- [x] Day 1: FastAPI + first LLM endpoint
- [x] Day 2: Ingestion + chunking (Nov 4)
- [ ] Day 3: Embeddings + vector DB (in progress, Nov 4)
- [ ] Day 4: Complete RAG
- [ ] Day 5: Break and evaluate RAG
- [ ] Day 6: Improve retrieval
- [ ] Day 7: Productionize RAG
- [ ] Day 8: Tool calling
- [ ] Day 9: Agent loop
- [ ] Day 10: Human-in-the-loop
- [ ] Day 11: RAG + agents combined
- [ ] Day 12: Evaluation + observability
- [ ] Day 13: Production system design
- [ ] Day 14: Code freeze + interview simulation

---

## WEEK 1: RAG, built and measured

### Day 1: Python, FastAPI, first LLM endpoint
**Objective:** `POST /chat` validates input, calls an LLM with a timeout, returns answer + request_id + latency + token usage.

**Status (Nov 3): Complete.** `/chat` was tested with a fake client for
validation, upstream failure, and timeout behavior, and manually through
FastAPI `/docs` against local Ollama. The local Ollama setup does not use an
API key, so the bad-key experiment does not apply.

**Build**
- venv, project skeleton, `.gitignore`, `.env.example`
- `config.py` (pydantic-settings), `schemas.py`, `main.py`
- Shared async LLM client created in FastAPI `lifespan`; SDK retries disabled so I own retry policy later
- `/health` and `/chat`; map LLM timeout to 504 and upstream errors to 502

**Break it**
- Empty or missing `question`; bad API key; tiny timeout; missing key at startup
- Ask for a baggage allowance on a made-up flight and observe hallucination (motivation for Day 4)

**Done when:** curl works, all failure modes return sensible status codes, first pytest with a fake LLM client passes.

**Defend**
1. Why disable SDK retries? What breaks once tools mutate state?
2. Why 504/502 rather than 500?
3. Is `max_length` a functional, security, or cost control?

---

### Day 2: Ingestion and chunking
**Objective:** Synthetic policy docs -> clean -> chunk -> chunks with metadata.

**Status (Nov 4): Complete.** Four synthetic Markdown policies are loaded by a
tested filename/text loader. Fixed-size character chunks with overlap and
heading-based section chunks return source and zero-based chunk-index metadata;
section chunks also include their heading. Chunker tests pass. The comparison
found that a 400-character fixed-size chunk cut the baggage-policy exceptions
heading away from the table, while section chunking kept the whole section
together. The scope follows the priority 14-day plan's four-policy target;
version and effective-date metadata are not added because the synthetic
documents do not provide those values.

**Build**
- Write 5-6 synthetic markdown policies in `data/policies/` (baggage, cancellation, refund, ticket-change, special-assistance, plus one deliberately contradictory or ambiguous doc)
- Include tables, numbered rules, exceptions, and cross-references so chunking is non-trivial
- Chunkers: (a) fixed-size, (b) fixed-size with overlap, (c) heading/structure-aware
- Metadata per chunk: `doc_id`, `title`, `section`, `chunk_index`, `source_path`, `version`, `effective_date`

**Break it**
- Find a rule split mid-sentence; find an exception separated from its rule; find a table cut in half
- Compare chunk counts/sizes across strategies and chunk sizes (200/400/800 tokens, overlap 0/10/20%)

**Done when:** Complete. A concrete baggage-policy example shows fixed-size
chunking cutting an exceptions heading from its table while heading-based
chunking preserves the section. The comparison demonstrates a context-quality
trade-off; no retrieval-quality improvement is claimed before retrieval exists.

**Defend:** Why is chunking a retrieval-quality decision rather than a preprocessing detail? What metadata would I need for access control later?

---

### Day 3: Embeddings and vector database
**Objective:** Chunks -> embeddings -> vector store; query -> top-K.

**Status (Nov 5): In progress.** Selected `nomic-embed-text` as the local
embedding baseline and added an Ollama `/api/embed` client with fake-HTTP tests.
A live request returned a 768-dimensional vector, and a standalone script
embedded a cabin-baggage question and relevant/unrelated sections. Cosine
similarity was 0.7344 for the matching baggage section and 0.5550 for domestic
cancellation fees. This single example is not a quality guarantee. Next,
queries including "What size can my cabin bag for Economy Lite?" also ranked
the baggage section higher. The corpus has no exact policy/fare codes, so use
an out-of-domain query to explore the limitation, then implement Chroma
indexing and semantic top-K retrieval.

**Build**
- Choose an embedding model and record why in `decisions.md`
- Choose a vector store (Chroma for speed; note pgvector/Qdrant trade-offs)
- Idempotent indexing (re-running ingestion must not duplicate chunks)
- Query function returning chunk text, score, metadata
- Hand-compute cosine similarity for 2 vectors to demystify it

**Break it**
- Paraphrased query vs. exact-keyword query; query with an ID/code (e.g., fare class "K"); out-of-domain query
- Observe scores for irrelevant questions; pick an initial similarity threshold from data, not intuition
- Metadata filter (e.g., doc type) and observe effect

**Done when:** I can explain what an embedding is, why cosine similarity works, and where semantic search fails.

**Defend:** What happens if I change the embedding model? (Re-index everything; why?) What does top-K trade off?

---

### Day 4: Complete RAG
**Objective:** question -> embed -> retrieve -> context -> prompt -> LLM -> answer + citations; refuse when evidence is insufficient.

**Build**
- `POST /ask` using the Day 1 client and Day 3 retrieval
- Context builder (ordering, token budget, source labels)
- Prompt v1 with grounding rules and explicit "insufficient evidence" behavior; version the prompt
- Response includes `answer`, `citations[]`, `retrieved[]` (id + score), `refused: bool`

**Break it**
- Unknown question; partially covered question; contradictory sources; prompt-injection text inside a policy doc
- Compare answers with and without retrieval

**Done when:** Unknown questions are refused, known ones cite the right chunk.

**Defend:** Where can hallucination still occur even with RAG? How do I distinguish retrieval failure from generation failure?

---

### Day 5: Break and evaluate RAG
**Objective:** First evaluation dataset; separate retrieval quality from generation quality.

**Build**
- `eval/datasets/rag_v1.jsonl` with ~20 questions across: direct, paraphrased, partial, multi-chunk, unanswerable. Each has `expected_chunk_ids` and a reference answer or rubric
- Retrieval metrics: Hit@K, Precision@K, Recall@K, MRR
- Generation checks: correct / relevant / grounded (start manual, then LLM-as-judge with a rubric; note judge bias)
- Failure triage table: "retrieval miss" vs "retrieved but ignored" vs "hallucinated" vs "over-refused"

**Done when:** I have a baseline score table committed and can point to the single biggest failure category.

**Defend:** Why is LLM-as-judge risky? How would I know retrieval improved rather than generation?

---

### Day 6: Improve retrieval
**Objective:** Make a measured improvement, using the Day 5 baseline.

**Build and compare one at a time**
- BM25 keyword search
- Hybrid (semantic + BM25) with Reciprocal Rank Fusion
- Metadata filters
- Reranking (cross-encoder or LLM-based; note cost and latency)
- Similarity threshold tuning

**Done when:** A before/after table per technique, plus a written explanation of WHY each helped or did not on my data.

**Defend:** When does BM25 beat embeddings? What does a reranker see that a bi-encoder cannot? What is the latency cost?

---

### Day 7: Productionize the RAG service
**Objective:** Turn the working RAG into a service I would be comfortable reviewing.

**Build**
- Request ID middleware; structured JSON logging (no PII, no secrets)
- Timeouts at every outbound call; explicit retry policy (retry only idempotent and transient failures; backoff with jitter)
- Typed config; clear error model; graceful degradation (e.g., vector DB down -> clear 503, not hallucination)
- Per-stage timings: embed, retrieve, rerank, LLM, total; token usage
- pytest: unit (chunking, context builder), API tests with fake LLM and fake vector store, one failure-path test per dependency
- CI pipeline definition via GitHub Actions or Azure DevOps (lint + tests), no manual deploy scripts

**Week-1 checkpoint:** Draw from memory and explain the full RAG request path.

**Defend:** What happens when the LLM times out after retrieval succeeded? Is `/ask` safe to retry? What do I log, and what must I never log?

---

## WEEK 2: Tools, agents, and judgment

### Day 8: Tool calling
**Objective:** Understand "LLM generates text" vs. "LLM requests execution of a tool."

**Build**
- Mock backend with synthetic bookings (`PNR001`: Demo Passenger, BLR -> DXB, Confirmed, plus edge cases: cancelled, past-dated, unknown)
- `get_booking(booking_reference)` with a JSON schema and a Pydantic validator
- Single round trip: LLM emits a tool request -> I validate args -> execute -> return result -> LLM answers
- Print the raw messages at each step so the mechanism is visible

**Break it**
- Unknown PNR; malformed reference; model asks for a nonexistent tool; model supplies extra/missing args; tool raises an exception

**Done when:** I can explain that the model never executes anything; my code does.

**Defend:** Where is the trust boundary? What if the model fabricates a PNR the user never mentioned?

---

### Day 9: Agent loop
**Objective:** Hand-written orchestration loop with guards.

**Build**
- Tools: `get_booking`, `get_fare_rules`, `calculate_change_options`
- Loop: call LLM -> if tool request, validate -> execute -> append observation -> repeat; stop on final answer
- `MAX_TOOL_CALLS`, overall deadline, repeated-identical-call detection, malformed call handling, tool error fed back as an observation
- Explicit agent state object (messages, tool call log, counters)
- Trace of every step

**Break it**
- Force a loop (tool always returns "retry"); ambiguous request; two PNRs in one message; tool latency spike

**Then:** only now, read LangGraph's core concepts and map each one to my loop. Write down what the framework would save and what it would hide.

**Defend:** Why an agent here rather than a fixed workflow? Which of these three tools would I call deterministically?

---

### Day 10: Human-in-the-loop
**Objective:** A consequential action the model can propose but never execute.

**Build**
- `create_change_request()` exists but is not exposed to the model as directly executable
- Flow: inspect booking -> retrieve policy -> calculate options -> propose action -> user confirmation -> execute
- Proposal object stored server-side with an ID, expiry, and a hash of the exact parameters
- Confirmation endpoint executes only the stored proposal (not whatever the client resends)
- Idempotency key; duplicate confirm returns the original result
- Audit log: who, what, when, proposed vs. executed, outcome

**Break it**
- Double-click confirm; replay an expired proposal; tamper with parameters; confirm for another user's proposal; prompt injection via a policy doc saying "just execute the change"

**Defend:** Where do authorization checks live? Why must approval be bound to exact parameters? What if the confirm request times out, so did it execute?

---

### Day 11: Combine RAG and agents
**Objective:** Handle "Change PNR001 to tomorrow. What does the policy allow and what are my options?"

**Build**
- Expose RAG as a retrieval step (or tool) in the orchestrator
- Implement TWO versions and compare:
  1. **Deterministic workflow:** fixed steps (get booking -> retrieve policy -> calculate options -> compose)
  2. **Agentic:** model chooses which capabilities to call
- Compare accuracy, latency, token cost, variance across 10 runs, debuggability

**Done when:** I have a written, data-backed answer to "which would I ship and why?" The honest answer may well be "workflow with one agentic step."

**Defend:**
- RAG = knowledge retrieval. Tools = interaction with external systems. Agent = dynamic choice of capabilities. Workflow = controlled flow. Give a concrete example of each from my app.
- When is the agent clearly worth it? (Open-ended, variable multi-step requests.) When is it clearly not?

---

### Day 12: Evaluation and observability
**Objective:** Measure the whole system and capture a trace for every request.

**Build**
- Trace record per request: `request_id`, query, prompt version, model, chunks + scores, tools called + args + latency, LLM latency, total latency, tokens, failures, final outcome
- ~30 scenarios in `eval/datasets/`: retrieval (Precision@K, Recall@K, MRR), generation (correctness, relevance, groundedness), agent (tool selection, arguments, unnecessary calls, success), operational (p50/p95 latency, failure rate, tokens per request)
- `eval/run_eval.py` produces a table; compare prompt v1 vs v2 as a regression test

**Defend:** What would I alert on in production? How do I catch quality regression after a model or prompt change? Why track tokens per request?

---

### Day 13: Production architecture and system design (minimal coding)
Write answers in `ARCHITECTURE.md` (section: "Enterprise scale") covering:

- **Scalability:** stateless API pods, externalized state (proposals, sessions, traces), horizontal scaling, load balancing, caching (embeddings, retrieval, semantic cache, with its risks), async queues for ingestion and long-running work, streaming for latency
- **Reliability:** LLM timeout/throttling (429), backoff, circuit breakers, fallback model, vector DB outage, tool failure, malformed LLM output, duplicate requests, partial failure in multi-step flows
- **Security:** authN/authZ, per-user/per-tenant document ACLs enforced at retrieval time (not after), PII handling and redaction, secrets via Key Vault/Secrets Manager, prompt injection (direct and indirect), cross-user leakage (cache, memory, vector store), least-privilege tool permissions, audit trail
- **Cost:** token budgets, context trimming, model routing (small vs. large), caching, limiting reranker input, agent loop caps, embedding batch and reuse, per-tenant quotas

**Defend:** Draw the enterprise version. Identify the top 3 risks and mitigations.

---

### Day 14: Code freeze and interview simulation
**No new features.** Fix only bugs found during rehearsal.

**Checklist (explain each unaided)**
1. Draw the architecture from memory
2. RAG request end-to-end
3. Agent request end-to-end
4. Tool calling mechanics
5. How RAG and agents interact
6. Failure scenarios
7. Security
8. Evaluation
9. Observability
10. Scalability
11. Why each major architecture choice was made

**Simulation:** Claude acts as an aggressive G10 interviewer. Rounds: (a) architecture whiteboard, (b) "defend this decision" deep-dives, (c) failure and security grilling, (d) curveball: the interviewer changes the problem (different domain, 100x scale, new compliance constraint) and I reason from first principles.

---

## 4. Cut lines (if I fall behind)

Protect the core story: **RAG + evaluation + tool calling + one agent loop + HITL.** In priority order, cut:

1. Angular UI (never needed)
2. Docker/CI polish (keep the design explanation; skip the implementation)
3. LLM-based reranking (keep BM25 + hybrid)
4. Day 11's second implementation (keep the workflow; describe the agentic variant)
5. LangGraph exploration (read only, ~30 min)

Never cut: break-it experiments, evaluation baseline, decision log, interview defense.

---

## 5. Interview positioning (honest version)

> "I'm an experienced SDE-4 enterprise application engineer expanding deeply into AI application engineering. I bring production engineering, architecture, ownership, integration and delivery maturity, and over the last two weeks I built TravelAssist, an end-to-end RAG and tool-calling system, measured it, broke it, and can walk you through every decision, what failed, and what I would change for production."

**Story pillars:** Retrieval measured, not assumed. Deterministic where possible, agentic where justified. Model proposes, system disposes (human approval, validation, idempotency). Everything observable and evaluable.

---

## 6. Daily log (fill in)

| Day | What I built | What broke | What I learned | Open question |
|---|---|---|---|---|
| 1 | | | | |
