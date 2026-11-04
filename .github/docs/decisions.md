# Architecture decisions

## Embedding model: Ollama `nomic-embed-text`

**Decision:** Use `nomic-embed-text` as the initial embedding model, served by
the project's local Ollama instance.

**Why:** The project already uses local Ollama for chat, and keeping embeddings
local avoids sending the synthetic policy corpus to another service. A single
small baseline is enough to build and understand the embedding and retrieval
pipeline.

**Trade-offs and follow-up:** This is a practical starting choice, not a claim
that it is the highest-quality model. The local Ollama server was unavailable
when the client was implemented, so a real model request and retrieval quality
have not yet been measured. Changing embedding models requires re-embedding
the corpus because vectors from different models are not directly comparable.
