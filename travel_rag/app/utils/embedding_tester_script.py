from app.utils.chunker import chunk_section
from app.utils.doc_reader import load_documents
from app.embeddings.client import OllamaEmbeddingClient
from app.config import get_settings
from app.vector_store.chroma_store import upsert_chunk, collection
import math
import httpx2, asyncio

async def embedding_test() -> None:
    settings = get_settings()
    docs = load_documents()
    chunks=[]
    for doc_select in docs:
        doc_chunk = chunk_section(doc_select[1], doc_select[0])
        chunks.extend(doc_chunk)
    async with httpx2.AsyncClient(
            base_url=settings.ollama_base_url,
            timeout=settings.ollama_timeout_seconds,
        ) as http_client:
        embedding_client = OllamaEmbeddingClient(
            http_client,
            settings.ollama_embedding_model,
        )
        embedding_question = await embedding_client.embed("What is the cabin baggage dimensions for main bag for business class?")
        for chunk_select in chunks:
            stored_chunk, embedding_vector = await embedd_and_store_chunk(chunk_select, embedding_client)
        result_ = find_most_similar_chunk(embedding_question, top_k=3)
        print(f"Most similar chunks:\n {result_}")

async def embedd_and_store_chunk(chunk_select, embedding_client):
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
    return stored_chunk, embedding_vector

def find_most_similar_chunk(embedding_vector, top_k=1):
    results= collection.query(
        query_embeddings=embedding_vector,
        n_results=top_k,
        include=["metadatas", "documents", "distances"],
    )
    return results

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