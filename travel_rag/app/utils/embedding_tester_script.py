from app.utils.chunker import chunk_section
from app.utils.doc_reader import load_documents
from app.embeddings.client import OllamaEmbeddingClient
from app.config import get_settings
from app.vector_store.chroma_store import upsert_chunk
import math
import httpx2, asyncio

async def embedding_test() -> None:
    settings = get_settings()
    docs = load_documents()
    doc_select=docs[1]
    chunks = chunk_section(doc_select[1], doc_select[0])
    chunk_select=chunks[2]
    async with httpx2.AsyncClient(
            base_url=settings.ollama_base_url,
            timeout=settings.ollama_timeout_seconds,
        ) as http_client:
        embedding_client = OllamaEmbeddingClient(
            http_client,
            settings.ollama_embedding_model,
        )
        embedding_vector_questions=await embedding_client.embed("What size can my cabin bag for Economy Lite?")
        embedding_vector = await embedding_client.embed(chunk_select['chunk'])
    stable_id = f"{chunk_select['source']}:{chunk_select['chunk_index']}"
    stored_chunk = upsert_chunk(
        embedding_vector=embedding_vector,
        text=chunk_select["chunk"],
        stable_id=stable_id,
        metadata={
            "source": chunk_select["source"],
            "chunk_index": chunk_select['chunk_index'],
            "section": chunk_select['section'],
        },
    )

    print(f"dimensions: {len(embedding_vector)}")
    print(f"dimensions questions: {len(embedding_vector_questions)}")
    print(f"similarity between chunk and question: {cosine_similarity(embedding_vector, embedding_vector_questions)}")
    print(f"stored chunk ID: {stored_chunk['ids'][0]}")
    print(f"stored metadata: {stored_chunk['metadatas'][0]}")
    print(f"stored text: {stored_chunk['documents'][0]}")

def cosine_similarity(vec_a,vec_b):
    """
    Job 1: Dot product (“how much do they agree?”)
    zip(a, b) walks both lists together, giving you (1, 4), then (2, 5), then (3, 6).
    """
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    
    """
    Magnitude (“how long is this list?”)

    For one list: square each number, add them up,
    take the square root. This is just the Pythagorean theorem 
    extended to many numbers.
    """
    magnitude_a = math.sqrt(sum(a * a for a in vec_a))
    magnitude_b = math.sqrt(sum(b * b for b in vec_b))
    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0
    return dot_product / (magnitude_a * magnitude_b)


if __name__ == "__main__":
    asyncio.run(embedding_test())