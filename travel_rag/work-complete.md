# Travel RAG: Progress checkpoint

Last verified: 2026-11-06

This is the project handoff for future chats. It records verified work, current
gaps, and the next step. The priority roadmap is
`../.github/docs/14-day-interview-plan.md`; the target design is
`../.github/docs/ARCHITECTURE.md`.

## Current status

- **Day 1 (FastAPI + first LLM endpoint): complete.**
- **Day 2 (ingestion + chunking): complete.** Four synthetic policies are
  loaded and chunked with fixed-size/overlap and heading-based strategies.
  Chunk records carry source, zero-based index, text, and section when
  structure-aware chunking is used.
- **Day 3 (embeddings + vector store): complete.** The Ollama embedding client
  passed fake-HTTP tests and returned a 768-dimensional vector in a live call.
  The standalone experiment indexes all 45 policy sections in persistent
  Chroma and retrieves top-K matches. The user observed relevant and
  out-of-domain query behavior; distances are not treated as confidence scores.
- **Day 4 (complete RAG): implementation in place; behavior validation remains.**
  `POST /ask` embeds, retrieves, builds labeled context and a grounding prompt,
  calls the chat model, and maps citations. Known-question citations and an
  out-of-domain abstention have been manually observed. Partial evidence,
  contradictory evidence, and prompt injection are not yet evaluated; model
  abstention is not deterministic.
- **Day 5 (break and evaluate RAG): in progress.** The user has authored a
  five-case seed dataset covering direct, paraphrased, multi-chunk, partial,
  and out-of-domain questions. Building the evaluation workflow and metrics
  remains the next task.

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
- Completed the Day 1 experiments: manually called `POST /chat` through
  FastAPI `/docs` against local Ollama and observed raw-chat behavior for the
  fictional `covid-travel-tax` question. The local Ollama setup does not use an
  API key, so the bad-key experiment does not apply. Timeout and upstream
  failures were covered with the fake chat client.
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
- Created four synthetic Markdown documents: ticket change, cancellation,
  baggage, and disruption policies.
- Added `app/utils/doc_reader.py` to load sorted Markdown files as
  `(filename, text)` pairs.
- Added `tests/test_doc_reader.py` to verify the four expected filenames and
  non-empty text for every policy.
- Verified the complete test suite with
  `cd travel_rag && ./.venv/bin/python -m pytest -q`: **11 passed** on
  2026-11-04.
- Added `app/utils/chunker.py` with fixed-size character chunks and configurable
  overlap. The loop stops after the final chunk, avoiding a redundant trailing
  chunk when the previous chunk already reached the end of the text.
- Added `tests/test_chunker.py` for overlap boundaries, empty and short text,
  final partial chunks, and invalid chunk size/overlap values.
- Verified `cd travel_rag && ./.venv/bin/python -m pytest tests/test_chunker.py -q`:
  **9 passed**; full suite `cd travel_rag && ./.venv/bin/python -m pytest -q`:
  **20 passed** on 2026-11-04.
- Updated both chunkers to return dictionary records with `source`,
  zero-based `chunk_index`, and `chunk`; section-based chunks also include a
  `section` heading. The fixed-size chunker uses character counts and overlap;
  section-based splitting keeps each `##` section together.
- Ran the chunking comparison on the synthetic baggage policy. With
  `chunk_size=400, overlap=0`, fixed-size chunk 1 ended in the middle of
  `### Cabin-baggage exceptions` and chunk 2 began with the remainder, apart
  from the cabin allowance table. The structure-aware chunk kept the table,
  heading, and exception rules together in section 2. This is the concrete
  example of chunk boundaries changing which context is available.
- Added chunk-index assertions to the chunker tests. Verified
  `cd travel_rag && ./.venv/bin/python -m pytest -q`: **21 passed** and
  `git diff --check` passed on 2026-11-04.
- Added `app/embeddings/client.py`, which sends text to Ollama's `/api/embed`
  endpoint and returns a vector. It maps timeout and service/response failures
  explicitly, rejects blank input and invalid vectors, and reuses the shared
  async HTTP client from the application lifespan.
- Updated the checkpoint and project/architecture roadmaps to mark Day 2
  complete and Day 3 in progress. Added `.github/docs/decisions.md` to record
  the initial embedding-model choice and its trade-offs.
- Selected `nomic-embed-text` as the local baseline embedding model and added
  `TRAVEL_RAG_OLLAMA_EMBEDDING_MODEL` configuration. The choice and trade-offs
  are recorded in `.github/docs/decisions.md`.
- Added fake-HTTP tests for successful embeddings, timeouts, upstream and
  malformed responses, empty vectors, and blank input. Verified
  `cd travel_rag && ./.venv/bin/python -m pytest tests/test_embeddings.py -q`:
  **7 passed**; full suite `cd travel_rag && ./.venv/bin/python -m pytest -q`:
  **28 passed** on 2026-11-04.
- On 2026-11-05, the user ran the Python embedding client against local Ollama
  with `nomic-embed-text`. It returned a 768-dimensional vector; the first
  five values were `[-0.037546925, 0.079259604, -0.1783307, -0.002847416,
  0.010480644]`. This verifies a live embedding request, not retrieval quality.
- The standalone `app/utils/embedding_tester_script.py` now selects the
  cabin-baggage section and successfully passes its text to the live embedding
  client. This verifies chunk-to-embedding flow for one real policy section.
- Extended the live experiment to embed the question "what cabin baggage can i
  bring?", the `2. Cabin baggage` section, and the `2. Domestic cancellation
  fees` section. All vectors had 768 dimensions. The observed cosine
  similarities to the question were **0.7344** for the relevant baggage
  section and **0.5550** for the unrelated cancellation section. This is one
  illustrative ranking result, not a threshold or quality guarantee.
- Tried two additional baggage queries against the same sections. For
  "Maximum main-bag dimensions?" the baggage and cancellation scores were
  **0.7155** and **0.4509**; for the paraphrase "What size can my cabin bag
  be?" they were **0.7877** and **0.5286**. In each trial the relevant section
  ranked higher. Since each query is a different vector, these small examples
  do not establish that one wording is inherently better or provide a
  production threshold.
- Added "What size can my cabin bag for Economy Lite?" as another query. The
  cabin-baggage and domestic-cancellation scores were **0.7757** and
  **0.5614**, respectively. The relevant section still ranked higher. The
  current synthetic policy files contain no exact policy/fare identifier
  codes, so use an out-of-domain query for the next limitation experiment
  rather than inventing a code example.
- The user verified a local persistent Chroma client by calling `heartbeat()`
  and opening/creating the `travel_rag_collection`. This verifies local
  database access only; no vectors or chunk records have been stored yet.
- Set the Chroma persistence path relative to `chroma_store.py` under
  `travel_rag/.chroma_db/`, which is covered by `travel_rag/.gitignore`.
- Updated the Chroma adapter to `upsert_chunk()`, passing Chroma's `ids`,
  `documents`, `embeddings`, and `metadatas` arguments. The embedding experiment
  now stores and reads back the cabin-baggage section using the stable ID
  `new-baggage-policy.md:2`.
- Ran `cd travel_rag && ./.venv/bin/python -m app.utils.embedding_tester_script`:
  the live embedding was 768 dimensions and Chroma returned the stored text and
  metadata. Re-running the script kept the collection count at **1**, verifying
  upsert behavior for this chunk. The full suite remains **28 passed**.
- On November 5, reorganized the application by responsibility:
  - Split API endpoints into `app/api/routes/chat.py` and
    `app/api/routes/operations.py`, composed by `app/api/routes/__init__.py`.
  - Moved document loading and chunking into `app/ingestion/`.
  - Extracted reusable embedding/upsert and vector-query operations into
    `app/ingestion/indexer.py` and `app/retrieval/retriever.py`.
  - Moved the experiment runner to `scripts/embedding_tester_script.py`; it
    coordinates indexing, query embedding, retrieval, and result display.
  - Updated application/test imports and project documentation to match.
- Verified the reorganized live experiment twice with
  `cd travel_rag && ./.venv/bin/python -m scripts.embedding_tester_script`.
  Each run indexed **45** sections, reported collection count **45**, and
  retrieved `new-baggage-policy.md:2` (`2. Cabin baggage`) as the top match
  for the cabin-baggage query. The repeat run confirms the existing records
  were updated rather than duplicated.
- Added offline unit tests for the indexer and retriever. Verified with
  `cd travel_rag && ./.venv/bin/python -m pytest -q`: **30 passed**, with one
  upstream Chroma deprecation warning. `git diff --check` passed.
- The user also tried an out-of-domain capital-city question. Chroma returned
  policy chunks anyway, with a top distance around **1.056**, compared with
  around **0.400** for a cabin-baggage question. These few observations
  illustrate nearest-neighbor behavior only and do not establish a reliable
  refusal threshold.
- Added `app/rag/context_builder.py` to convert Chroma's already-ranked,
  nested result lists into source-labeled context while preserving retrieval
  order. The user's live output included the cabin-baggage section and its
  infant exception. This formats evidence; it does not rank or filter it.
- Corrected the context label's `ID::` punctuation and added focused tests for
  source/text labels, preserved result order, and empty search results.
  Verified with `cd travel_rag && ./.venv/bin/python -m pytest
  tests/test_context_builder.py -q`: **2 passed**; `git diff --check` passed.
- Implemented `app/rag/prompt_builder.py` to combine the question and labeled
  context with rules for evidence-only answers, `[Source N]` citations,
  insufficient evidence, and treating retrieved text as untrusted reference
  material. Added a unit test verifying all required prompt parts are included.
  Verified with `cd travel_rag && ./.venv/bin/python -m pytest
  tests/test_prompt_builder.py -q`: **1 passed**; `git diff --check` passed.
- Updated `app/rag/response_formatter.py` so both `[Source N]` and full
  `[Source N | ...]` citations map to the Nth Chroma result. Citation IDs,
  source filenames, sections, and chunk indexes come from Chroma metadata, not
  model-echoed fields. Duplicate labels are returned once; labels without a
  corresponding result are omitted. The answer text and full retrieved list
  remain unchanged.
- Made the prompt's citation requirement explicit: each factual sentence or
  bullet must end with the exact `[Source N]` label(s), with a short example.
  This guides model output but cannot guarantee compliance; the response
  formatter still returns no citations when the answer contains no valid label.
- Added an explicit insufficient-context phrase to the prompt and a formatter
  helper that sets `refused` when that phrase occurs in the model answer. This
  is a model-reported refusal signal, not a guarantee that every unsupported
  answer will be detected or that an answer containing the phrase has no
  unsupported claims.
- Manually asked `/ask` for the capital of India. Chroma returned three
  unrelated policy chunks (observed distances approximately 1.056, 1.077, and
  1.107), while the model answered that the context did not contain the
  information and declined. The user also observed occasional answers from
  the model's own knowledge despite the prompt. These examples demonstrate
  that nearest-neighbor results can exist for an unanswerable question and
  that prompt-based abstention is not reliable enough to certify grounding.
- Added formatter tests and `/ask` route tests for citation mapping,
  deduplication, out-of-range references, returning all retrieved matches, and
  refusing without a model call when retrieval is empty. Verified
  `cd travel_rag && .venv/bin/python -m pytest -q
  tests/test_prompt_builder.py tests/test_response_formatter.py tests/test_chat.py`:
  **15 passed** on 2026-11-06; `git diff --check` passed.
- Reviewed `eval/datasets/rag_v1.jsonl`: it now has five unique, valid JSONL
  cases covering direct, paraphrased, multi-chunk, partial, and out-of-domain
  questions. Corrected the partial case to `answerable: true` because one
  requested part has supporting evidence; its category and answerable/
  unanswerable part lists express the partial coverage. Verified all expected
  chunk IDs exist in the 45-record local Chroma collection.
## Not implemented yet

- Evaluation runner and retrieval metrics; expansion of the seed set toward
  12-15 cases; generation quality, refusal-correctness, groundedness, and
  failure-triage measurements.
- Contradictory and prompt-injection examples/evaluations. Phrase-based `refused`
  detection remains dependent on model behavior; no retrieval-based refusal
  threshold is established.
- Tool calling, agent flows, human approval, and observability beyond the
  request ID and chat response metrics.

## Next step

Implement the first retrieval metrics against the five authored cases (Hit@K
and MRR are a focused starting point), then expand the dataset toward the
priority roadmap's 12-15 cases. Add generation quality/refusal checks separately
so retrieval misses can be distinguished from evidence retrieved but ignored
or over-refused. Do not select a distance-based refusal threshold until it has
been evaluated. `/chat` remains raw chat and does not use retrieved evidence.

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
