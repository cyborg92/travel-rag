import asyncio

import httpx2

from app.config import get_settings
from app.embeddings.client import OllamaEmbeddingClient
from app.ingestion.chunker import chunk_section
from app.ingestion.doc_reader import load_documents
from app.ingestion.indexer import index_chunks
from app.retrieval.retriever import find_most_similar_chunks
from app.vector_store.chroma_store import collection

QUESTION = "What is the cabin baggage dimensions for main bag for business class?"


async def embedding_test() -> None:
    settings = get_settings()
    chunks = [
        chunk
        for filename, text in load_documents()
        for chunk in chunk_section(text, filename)
    ]

    async with httpx2.AsyncClient(
        base_url=settings.ollama_base_url,
        timeout=settings.ollama_timeout_seconds,
    ) as http_client:
        embedding_client = OllamaEmbeddingClient(
            http_client,
            settings.ollama_embedding_model,
        )
        indexed_count = await index_chunks(chunks, embedding_client)
        print(f"Chunks indexed: {indexed_count}")
        print(f"Collection count: {collection.count()}")

        query_embedding = await embedding_client.embed(QUESTION)
        results = find_most_similar_chunks(query_embedding, top_k=3)

    for rank, (chunk_id, document, metadata, distance) in enumerate(
        zip(
            results["ids"][0],
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ),
        start=1,
    ):
        print(
            f"\nResult {rank}: {chunk_id} "
            f"(distance={distance:.4f}, metadata={metadata})\n{document}"
        )


if __name__ == "__main__":
    asyncio.run(embedding_test())
