from app.embeddings.client import EmbeddingClient
from app.vector_store.chroma_store import upsert_chunk


async def index_chunks(
    chunks: list[dict],
    embedding_client: EmbeddingClient,
) -> int:
    indexed_count = 0
    for chunk in chunks:
        embedding_vector = await embedding_client.embed(chunk["chunk"])
        metadata = {
            "source": chunk["source"],
            "chunk_index": chunk["chunk_index"],
        }
        if "section" in chunk:
            metadata["section"] = chunk["section"]
        stable_id = f"{chunk['source']}:{chunk['chunk_index']}"
        upsert_chunk(
            embedding_vector=embedding_vector,
            text=chunk["chunk"],
            stable_id=stable_id,
            metadata=metadata,
        )
        indexed_count += 1
    return indexed_count
