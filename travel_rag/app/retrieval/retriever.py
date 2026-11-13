from typing import Any

from app.vector_store.chroma_store import collection


def find_most_similar_chunks(
    embedding_vector: list[float],
    top_k: int = 3,
) -> dict[str, Any]:
    return collection.query(
        query_embeddings=[embedding_vector],
        n_results=top_k,
        include=["metadatas", "documents", "distances"],
    )
