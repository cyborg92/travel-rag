My 14-Day SDE-4 AI Interview Plan
Progress as of November 5: Day 1 (FastAPI + first LLM endpoint) and Day 2
(synthetic document ingestion and chunking) are complete. Day 3 (embeddings
and vector DB) is in progress: the Ollama embedding client passed fake-HTTP
tests and returned a 768-dimensional vector in a live `nomic-embed-text`
request. Similarity comparison and vector storage remain. See
`../../travel_rag/work-complete.md` for verified details and validation
results.

The goal
I am not trying to learn every GenAI technology before the interview.
I am trying to accomplish one thing:
Personally build one end-to-end Travel AI system and become capable of defending every important engineering decision at SDE-4 depth.
My interview positioning is:
I am already an SDE-4 engineer with enterprise engineering, architecture, integration, production, reliability, and delivery experience. I am now applying that engineering maturity to AI systems.
I should not pretend that two weeks of work equals years of production GenAI experience.
Instead, I'll demonstrate that I understand the mechanics by actually building them, measuring them, deliberately breaking them, and reasoning about how they would work in production.
That is consistent with the positioning already captured in plan.
The application I will build
I will build TravelAssist AI, using only synthetic travel data.
The flagship scenario is:
"I need to change PNR001 to tomorrow. What does the applicable policy allow, and what options do I have?"
The final conceptual flow is:
Plain Text
User
|
v
FastAPI
|
v
Orchestration
/ \
/ \
v v
RAG Tools
| |
Policy retrieval Booking
| Fare rules
Semantic + BM25 Options
| |
+------v------+
|
LLM
|
Grounded answer
+ citations
|
if action requested
|
v
PROPOSE
|
Human approval
|
v
EXECUTE
 
Evaluation + Observability
across everything
This deliberately combines RAG, tool calling, agents/workflows, human approval, evaluation, observability and production engineering, which are already the core capabilities in my target architecture.
The most important rule
Depth beats breadth.
I don't need:
Angular UI
Multi-agent systems
Kubernetes deployment
Fancy dashboards
model fine-tuning
complicated LangChain abstractions
five vector databases
sophisticated rerankers
100 evaluation questions
every possible AI framework
I need:
RAG + evaluation + hybrid retrieval + tool calling + one bounded agent loop + HITL + production reasoning.
These are the core elements to protect even if I fall behind. plan explicitly identifies RAG, evaluation, tool calling, one agent loop and HITL as the protected core.
Phase 1: Build and understand RAG
November 3-6
First build the simplest complete chain:
Plain Text
Question
↓
Embedding
↓
Retrieval
↓
Relevant policy chunks
↓
Context construction
↓
LLM
↓
Grounded answer + citation
Step 1: LLM
Start with:
Plain Text
POST /chat
I need to understand a raw LLM request before introducing RAG.
Implement:
FastAPI
Pydantic
LLM client
timeout
request ID
latency
proper error responses
tests with fake LLM client
Then deliberately ask something the model has no evidence for.
Observe it hallucinate.
That gives me the reason for RAG rather than simply memorizing its definition.
Day 1 completed November 3: `/chat` passed fake-client validation, timeout, and
upstream-failure tests and was manually exercised through FastAPI `/docs`
against local Ollama. The local Ollama setup does not use an API key, so the
bad-key experiment does not apply. The fictional `covid-travel-tax` question
produced a related generic answer rather than an uncertainty response.
Step 2: Chunking
Day 2 completed November 4: four synthetic Markdown policies and a tested
filename/text loader are present. Fixed-size character chunks with overlap
and heading-based section chunks return source and chunk-index metadata;
section chunks also identify their heading. Tests pass. In the baggage-policy
comparison, fixed-size chunking at 400 characters cut the cabin-baggage
exceptions heading at a chunk boundary, while section chunking kept the
allowance table and its exceptions together.
Create roughly four synthetic travel-policy documents:
ticket change
cancellation
baggage
disruption
Include awkward features intentionally:
exceptions
headings
tables
policy codes
contradictory information
rules spanning paragraphs
Implement only 2 useful chunking strategies:
Plain Text
fixed + overlap
vs
structure-aware
Find at least one concrete example where a bad chunking strategy separates an exception from the governing rule.
The interview lesson is:
Chunking isn't merely preprocessing. It changes what evidence retrieval can return and therefore directly affects answer quality.
Step 3: Semantic retrieval
Day 3 started November 4: selected `nomic-embed-text` as the local embedding
baseline and implemented an Ollama embedding client. Fake-HTTP tests pass, and
a live request on November 5 returned a 768-dimensional vector. The standalone
experiment embedded a cabin-baggage question and matching/unrelated policy
sections. Cosine scores were 0.7344 for the baggage section and 0.5550 for
domestic cancellation fees. This is one comparison, not a threshold or quality
guarantee. Further cabin-baggage queries also ranked the relevant section
higher. The current synthetic corpus has no exact policy/fare codes, so use an
out-of-domain query for the limitation experiment. Chroma indexing and
semantic retrieval remain.
Implement:
Plain Text
chunks
↓
embedding model
↓
vectors
↓
Chroma
Then:
Plain Text
question
↓
query embedding
↓
similarity search
↓
top-K chunks
Understand:
Embeddings
cosine similarity
top-K
thresholds
metadata
why changing embedding models generally requires re-indexing
Most importantly, discover limitations yourself.
For example:
Plain Text
Paraphrase:
"What fees apply when I move my trip?"
 
→ semantic retrieval should be useful.
But:
Plain Text
"FARE-K"
"POLICY-1234"
might expose weaknesses of pure semantic retrieval.
Step 4: Full RAG
Now construct:
Plain Text
question
↓
retrieve evidence
↓
construct bounded context
↓
grounded prompt
↓
LLM
↓
answer + citation
The system MUST support:
Known question
Answer using retrieved evidence.
Unknown question
Return:
Insufficient evidence.
rather than asking the LLM to invent something.
Contradictory sources
Reveal the ambiguity.
Prompt injection in retrieved documents
Treat the retrieved document as data, not instructions.
These behaviors are already explicit security and reliability principles in my architecture.
Phase 2: Measure rather than assume
November 7-8
Build approximately 12-15 meaningful questions.
Include:
direct questions
paraphrases
exact-code queries
multi-chunk questions
unanswerable queries
contradictory policy
prompt-injection case
Measure a small number of understandable metrics:
Plain Text
Hit@3
MRR
Refusal correctness
Groundedness
I need to distinguish:
Plain Text
RETRIEVAL FAILURE
 
Evidence never reached the LLM
from:
Plain Text
GENERATION FAILURE
 
Correct evidence reached the LLM,
but the model generated a bad answer.
This distinction is fundamental to debugging RAG and is explicitly part of my architecture's evaluation model.
Then improve retrieval
Add:
Plain Text
Semantic search
+
BM25
+
Reciprocal Rank Fusion
Test why each behaves differently.
My eventual interview explanation should come from real measurements:
Semantic search worked better on paraphrases, while BM25 helped with exact identifiers. Hybrid retrieval improved coverage because the two retrieval approaches failed differently.
Don't say hybrid is better just because a course says so.
Measure it.
Phase 3: Understand tools
November 9
This is probably one of the most important concepts to deeply understand.
Start with:
Python
get_booking("PNR001")
Understand the exact sequence:
Plain Text
User
↓
LLM sees tool schema
↓
LLM REQUESTS
get_booking(PNR001)
↓
Application validates
↓
Application authorizes
↓
Application executes Python
↓
Tool result
↓
returned to LLM
↓
LLM composes answer
My key interview sentence:
The model doesn't execute the tool. It proposes a structured tool call. My application remains the trust boundary and validates, authorizes and executes that request.
This exact separation is central to the tool-calling architecture I've designed.
Deliberately test:
invalid PNR
nonexistent tool
missing argument
extra argument
timeout
exception
Phase 4: Understand agents
November 10
Build a tiny agent loop myself.
No LangGraph initially.
Conceptually:
Python
while steps < MAX_STEPS:
 
response = llm(messages, tools)
 
if response.is_final:
return response
 
call = response.tool_call
 
validate(call)
 
result = execute(call)
 
messages.append(result)
Then discover why this isn't sufficient.
Introduce:
MAX_TOOL_CALLS
overall deadline
argument validation
unknown-tool rejection
duplicate-call detection
tool timeouts
state
tracing
Force the agent into bad behavior.
For example:
Plain Text
Agent → tool
Tool → retry
Agent → same tool
Tool → retry
Agent → same tool
...
Then understand why loop limits exist.
Only after this should I look at LangGraph and think:
"Okay, now I understand what this framework is abstracting."
That is already a hard rule in my preparation plan.
Phase 5: Human-in-the-loop
November 11
This is where the project begins to demonstrate SDE-4 engineering judgment rather than just AI API knowledge.
An LLM should NEVER directly perform:
Plain Text
Change booking
Issue refund
Cancel itinerary
etc.
Instead:
Plain Text
Agent evaluates request
↓
Retrieves applicable policy
↓
Calculates available options
↓
Creates PROPOSAL
↓
User reviews exact action
↓
User CONFIRMS
↓
Backend validates proposal
↓
EXECUTE
The proposal lives server-side and contains:
Plain Text
proposal_id
owner
exact parameters
parameter hash
expiry
status
Confirmation refers to the proposal.
The client cannot say:
JSON
{
"confirm": true,
"new_destination": "something different"
}
and modify the approved action.
The server executes exactly what was approved.
Then implement idempotency so:
Plain Text
CONFIRM
CONFIRM
CONFIRM
does not execute the action three times.
My architecture explicitly uses stored proposals, ownership, parameter hashing, expiry and idempotency for this reason.
Phase 6: Put everything together
November 12
Focus on ONE flagship workflow:
"Change PNR001 to tomorrow. What does the policy allow and what are my options?"
Prefer the deterministic production flow:
Plain Text
get_booking
↓
retrieve applicable policy
↓
calculate change options
↓
LLM explains options
↓
citations
↓
user selects
↓
proposal
↓
confirmation
↓
execute
Don't assume everything should be agentic.
In fact, one of my strongest architectural positions should be:
Deterministic where possible, agentic where justified.
For known business workflows, deterministic orchestration provides:
lower variability
better testing
easier debugging
predictable latency
lower model usage
clearer audit trail
Use an agent when the request's sequence genuinely cannot be determined beforehand.
That workflow-first choice is already one of the explicit decisions in ARCHITECTURE.
Phase 7: Make everything observable
Every meaningful request should produce something like:
Plain Text
request_id
 
model
prompt_version
 
retrieval:
chunks
scores
strategy
 
tools:
names
arguments
duration
results
 
LLM:
duration
tokens
 
total_latency
 
outcome
 
errors
I need to be able to answer:
How do you debug an answer that was wrong yesterday?
And say:
I correlate by request ID, inspect the prompt/model version, retrieved chunks and scores, tool executions, model response and latency, then determine whether the failure came from retrieval, generation, orchestration or a downstream dependency.
The required per-request trace and metric families are already laid out in my architecture.
Phase 8: Stop coding and think like SDE-4
November 13-14
Now stop adding features.
Take the small local project and ask:
What changes if this becomes a real enterprise service?
Be able to reason about:
Scalability
Plain Text
stateless API
load balancer
horizontal scaling
external state store
managed vector DB
caching
queues
streaming
Reliability
Plain Text
LLM timeout
429/throttling
vector DB unavailable
tool failure
partial execution
model malformed output
retry storm
duplicate requests
circuit breaker
fallback
 
Security
Plain Text
authentication
authorization
document ACL
PII
prompt injection
indirect prompt injection
cross-user leakage
tool permissions
secrets
audit
Cost
Plain Text
token budgets
context trimming
small vs large models
caching
agent-loop caps
batch embeddings
tenant quotas
Governance
Plain Text
prompt version
model version
evaluation gates
release process
rollback
quality monitoring
audit trail
These concerns are already identified in my enterprise-scale architecture.
I do not need to implement all of this.
I need to reason about it convincingly.
November 15-16: Stop building
NO NEW FEATURES.
The project is frozen.
Now transform two weeks of work into interview evidence.
I should be able to draw from memory:
Plain Text
USER
↓
FastAPI
↓
Orchestrator
/ \
↓ ↓
RAG Tools
/ \ ↓
Semantic BM25 Booking system
\ / |
Hybrid |
\ /
\ /
LLM
↓
Response
↓
Human approval
↓
Action
And defend every arrow.
My five most important interview stories from TravelAssist
By November 16, I want five concrete technical stories:
1. Chunking failure
Here's how a policy exception was separated from the main rule and how changing chunking improved retrieval.
2. Retrieval failure
Here's where semantic search failed and BM25/hybrid retrieval helped.
3. Hallucination/refusal
Here's how the model behaved without sufficient evidence and how I designed explicit refusal.
4. Agent failure
Here's how my agent repeated a tool call or behaved incorrectly and what guards I added.
5. Consequential-action safety
Here's why I separated propose/confirm/execute and implemented server-side proposals and idempotency.
These stories are more valuable than saying:
"I know RAG, LangChain and agents."
But TravelAssist proves AI capability, not my entire SDE-4 capability
This distinction is extremely important.
I already have professional experience.
TravelAssist should prove:
Can Rachit apply SDE-4 engineering thinking to AI?
My existing experience should prove:
Is Rachit an SDE-4 engineer?
Therefore I also need approximately six real career stories about:
Architecture/design I led
Major production issue I handled
Difficult technical disagreement
Cross-team dependency I resolved
Technical debt vs delivery trade-off
Mentoring/raising engineering quality
For each:
Plain Text
Context
↓
Problem
↓
My responsibility
↓
Options
↓
Decision
↓
Trade-offs
↓
Influence
↓
Result
↓
What I'd do differently
What I absolutely WILL NOT do
If I'm behind, I will cut features rather than sacrifice understanding.
First things to remove:
Angular UI
Docker/deployment work
CI polish
sophisticated reranking
duplicate workflow/agent implementation
extensive LangGraph work
additional policy documents
huge evaluation dataset
The core survives:
Plain Text
RAG
+
Evaluation
+
Hybrid retrieval
+
Tool calling
+
Bounded agent
+
HITL
+
Observability
+
SDE-4 architecture reasoning
This is consistent with the explicit cut strategy in plan.
The daily rule
Every day I need to answer six questions:
1. What did I build?
2. How does it actually work?
3. What broke?
4. Why did it break?
5. What trade-off did I make?
6. How would my design change in production?
If I can't answer those questions without Copilot, the milestone isn't complete.
This reinforces the build/break/defend loop and decision logging already specified in plan.
What success looks like on November 17 at 10 AM
Success is NOT:
"I implemented 48 features."
Success is being asked:
"Why did you use hybrid retrieval?"
and replying:
"I started with semantic retrieval and measured it against a small labelled dataset. It worked well for paraphrases but struggled with exact travel policy identifiers. I added BM25 and fused the rankings. Here's what changed..."
Then they ask:
"Why an agent?"
And I say:
"For this particular booking-change flow, I actually wouldn't use a fully agentic design in production. The sequence is known and consequential, so I prefer deterministic orchestration. I'd use agentic decision-making when the user's goal is open-ended and the appropriate capability sequence cannot be predetermined."
Then:
"What if the agent tries to change a booking?"
And I say:
"It can't. The model can propose an action, but application code owns authorization and execution. A consequential operation creates a server-side proposal containing the exact approved parameters. Execution requires explicit human confirmation, verifies ownership and expiry, and uses idempotency to prevent duplicate execution."
Then:
"How do you know your AI system is actually good?"
And I say:
"I don't treat 'the demo looked good' as evidence. I maintain a labelled evaluation dataset and separate retrieval metrics from generation metrics and agent metrics. That lets me tell whether a regression came from retrieval, generation or orchestration."
That's the interview we're preparing for.
The one sentence to remember for the next 14 days
I am not trying to learn all of AI. I am building one serious AI system deeply enough that I can explain how it works, demonstrate where it fails, show how I measured it, defend my design decisions, and explain how my existing SDE-4 production engineering experience would take it from a local prototype to a secure, reliable, scalable enterprise product.
That is the plan.