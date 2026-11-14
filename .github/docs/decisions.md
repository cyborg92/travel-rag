# Architecture decisions

## Embedding model: Ollama `nomic-embed-text`

**Decision:** Use `nomic-embed-text` as the initial embedding model, served by
the project's local Ollama instance.

**Why:** The project already uses local Ollama for chat, and keeping embeddings
local avoids sending the synthetic policy corpus to another service. A single
small baseline is enough to build and understand the embedding and retrieval
pipeline.

**Trade-offs and follow-up:** This is a practical starting choice, not a claim
that it is the highest-quality model. A live request returns 768-dimensional
vectors, and retrieval quality is measured on the labelled eval set (see Hybrid
retrieval below); other embedding models have not been compared. Changing
embedding models requires re-embedding the corpus because vectors from
different models are not directly comparable.

## Build versus use a library

**Decision:** Use well-known libraries for commodity components; hand-build only
the mechanisms that are the project's architectural story (RAG path wiring,
evaluation harness, tool trust boundary, bounded agent loop, propose/confirm/
execute with idempotency).

**Why:** Time belongs on the parts that decide whether the system is correct
and safe, not on algorithms that are an import in a real project. The in-repo
BM25 implementation took about a day of tokenizer, indexing and scoring detail;
a production system would use a library or the keyword search of its search
service.

**Trade-offs and follow-up:** A library hides internals, so each one still has to
be understood well enough to say what it does, how it fails, and how it is
measured on the eval set. `app/retrieval/bm25.py` stays as a tested, finished
component and is not extended; further keyword-search work uses a library.

## Hybrid retrieval (semantic + BM25 with RRF)

**Decision:** Retrieve with both semantic search and BM25 and merge the
rankings with Reciprocal Rank Fusion (k=60). Adopt it as the retrieval
candidate to wire into `/ask`; it is not wired yet.

**Why:** On the 12 answerable eval cases at top 3, hybrid scored Hit@3 1.000,
Recall@3 0.875, MRR 0.861, against semantic 1.000 / 0.833 / 0.847 and BM25
0.917 / 0.792 / 0.833. The two methods failed on different cases (BM25 missed a
paraphrase; semantic search missed a literal-wording case), and fusion recovered
both. RRF uses ranks only, so cosine distances and BM25 scores need no
normalisation.

**Trade-offs and follow-up:** The improvement is small (one or two cases out of
twelve) and untested on more data. Multi-chunk questions (q003, q008, q009) are
not improved by any strategy. Hybrid adds a second index and fusion step. In
production the keyword side would come from the search service rather than the
hand-written `bm25.py`.

## Tool trust boundary: validate shape in the registry, authorize in the data layer

**Decision:** Each tool is registered with a Pydantic argument model
(`extra="forbid"`, reference pattern `^PNR\d{3}$`) and executed only through
`execute_tool`, which rejects unknown tools, validates arguments, and turns every
failure into a string observation for the model. The caller's `user_id` is passed
by application code, is not part of any tool schema, and is enforced inside
`get_booking`, which raises the same `BookingNotFoundError` for a missing booking
and for another user's booking.

**Why:** Model output is untrusted input. Validation proves the shape of a
request, not that the caller may see the data; a fabricated but well-formed
reference such as PNR004 passes the schema. Keeping the identity out of the
schema means the model cannot claim to be someone else, and a model-supplied
`user_id` is rejected by `extra="forbid"`. Putting the check next to the data
keeps `execute_tool` generic and means a future tool cannot be called without
accepting an identity. Returning the same error for "missing" and "not yours"
stops the model, and through it the user, from probing which references exist.
Unexpected tool exceptions return a generic message and are logged, so internal
details do not reach the model.

**Trade-offs and follow-up:** Authorization in each tool function relies on every
new tool implementing it; the signature forces the parameter, not the check.
The identity is a constant in the experiment script; the FastAPI app still needs
an authenticated identity. The designed change flow needs its own ownership
check, bound to the stored proposal.

## Tool registry: one record per tool, written for the model

**Decision:** Describe each tool with a frozen `ToolSpec` (name, description,
argument model, function) in `app/tools/registry.py`, keep argument models in
`app/tools/schemas.py`, and write each description for the model, including
what the tool does not return and which tool to use instead. Results are
Pydantic models, so `execute_tool` serializes any tool the same way. Where a
tool starts from a booking, it loads it through `get_booking(reference,
user_id)` so the owner check is inherited; a pure helper takes the trusted
booking. An unknown fare class is treated as a data bug: it raises `KeyError`,
which the executor logs and reports to the model as a generic failure.

**Why:** The description is the only thing the model reads when choosing a
tool, and the earlier positional pair `(schema, function)` had nowhere to put
one. With two tools the descriptions decided the choice: "route of PNR001"
called `get_booking` and "can I change PNR005" called `get_fare_rules`. Having
the tool load the booking itself keeps booking data out of model-supplied
arguments, which would let the model assert its own fare class.

**Trade-offs and follow-up:** Tool choice was observed in one run per question
with one local model; it is not a measured selection accuracy. Results still
include internal fields such as `owner_id`; a trimmed result model would
remove them. Each tool function must still accept `user_id` and use it; the
signature enforces the parameter, not the check.

## Final-answer completeness: facts go in the tool result, the prompt asks, code checks and appends

**Decision:** Put every fact the answer depends on into the tool result as data
(the amounts' currency is a `currency` field, credits are explicit fields, and
caveats are in `notes`); tell the model in the system prompt to report credits
and repeat notes and to ask for missing inputs; and treat a code-level check or
a pre-built summary as the production fix, not built yet.

**Why:** A note about INR in the tool description did not stop the model from
writing dollars; adding `"currency":"INR"` to the result did, because the
model reads the result when it writes the answer, not the tool list. Relaying
the tax note varied between runs with an identical result. With the prompt
(3 runs, one local model) the credit appeared in 2 of 3 answers and the tax
note in 2 of 3, never both in the same run, and one answer claimed a booking
"will be changed" when the tool only quotes.

**Trade-offs and follow-up:** The options are (A) prompt instructions: cheap,
improves but is never guaranteed; (B) a `summary` sentence built in code that
the model repeats: fewer things to omit, more code, and the model can still
paraphrase badly; (C) a check after the answer that appends or rejects missing
credits and notes: most reliable and the right choice for anything that affects
what a passenger pays, but it adds a step and needs a definition of "contains".
Only A is in place. The observations are small samples; a real rate needs
generation scoring in the evaluation harness. The "will be changed" claim
matters most for the human-approval flow: the model must not state that a change
happened.

**Update (checks built):** after the loop's final reply, code now (1) appends
any note or credit from the tool results that the answer lacks (notes matched
by exact text, credits by amount) and (2) appends a "confirmed figures" line per
successful quote, built from the result. Live runs showed why both were needed
and where they stop. Across 5 runs on one local model: a credit dropped, a note
dropped, a note paraphrased (so appended again as a duplicate), a quote with a
wrong total (the model wrote 3500 + 23300 = 24000 when the total to pay was
3500; the right number was also in the answer as the change fee, so a "contains
the total" check would have passed it, and the confirmed-figures line is what
corrects it), and twice a tool call written as text instead of made, once as
raw JSON and once as "Now, calling the tool for PNR006". The checks guarantee
that the facts and the true figures are shown; they do not make the model's own
sentences correct, and a sentence that only mentions a note counts as
presenting it. The production answer for money is option B in full: the code
renders every amount and the model writes only the surrounding words. Text
that imitates a tool call is handled separately, below.


## Agent loop: guards enforced in code, in a fixed order

**Decision:** Run the model-and-tools loop under three guards that the model
cannot talk its way past: a deadline checked at the top of each round, a call
limit checked before each individual request, and a duplicate check (tool name
plus arguments with sorted keys) that skips a repeat and tells the model to use
the earlier result. Each stop returns a `stop_reason`. The model function and
the clock are passed in rather than created inside the loop.

**Why:** The model decides how many rounds happen, so the code must decide when
they stop. The limit is checked per request, not per round, because one reply
can carry several requests: a per-round check would let a reply of seven requests
run past a limit of five. Skipped duplicates do not count toward
the limit, which keeps a harmless repeat from spending the budget, but it means
a model that only repeats itself never reaches the limit; the deadline is what
bounds that case, and a test forces it. Injecting the clock and the model made
every stop reason testable with no network and no waiting. On a live local
model the loop finished in two tool calls and answered; the guards did not
trigger.

**Trade-offs and follow-up:** The deadline is checked between rounds, so one
hung model call is bounded only by the HTTP timeout, and a slow tool is not
bounded at all; a per-tool timeout is designed and unbuilt because the current
tools are in-memory. A limit stop returns a fixed message, not an explanation
from the model. The duplicate rule treats any identical repeat as wasted, which
would be wrong for a tool whose result changes over time; the current tools are
read-only quotes. The final answer can still omit credits or notes (two live
runs dropped a different one each time), so the completeness check above
remains the open item.

## Tool requests written as text: recover the strict case, keep the trust boundary

**Decision:** When a reply has no `tool_calls` but its text is, in its entirety,
a JSON object with a `name` that is a registered tool and `parameters` or
`arguments` that is an object, treat it as a tool request. It enters the same
path as a real request, so schema validation, the owner check, the call limit,
the duplicate check and the deadline all apply, and the loop logs a warning.
Real `tool_calls` always win over text.

**Why:** In 2 of 8 live runs the local model wrote a request as text, once as
raw JSON and once as a promise ("Now, calling the tool for PNR006"). The loop
saw no tool calls and returned that text as the final answer, so a booking was
never quoted and the passenger saw JSON. Recovering the strict shape is a few
lines, deterministic and tested with the fake model. It does not weaken the
trust boundary: identity still comes from the caller (a model-supplied
`user_id` is still rejected) and an unknown tool name is ignored.

**Trade-offs and follow-up:** Only a reply that is entirely the request is
recovered; JSON mixed into prose is left as the answer, and a promise to call a
tool cannot be recovered because it contains no request. Both remain known
gaps. A lenient parser raises the risk of executing JSON the model merely
quoted, which is why the name must be a registered tool. Observed on one local
model; the three live runs after the change did not trigger the path, so the
unit tests are the evidence it works, not a live recovery.
