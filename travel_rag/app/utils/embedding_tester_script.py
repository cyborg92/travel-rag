from app.utils.chunker import chunk_section
from app.utils.doc_reader import load_documents
from app.embeddings.client import OllamaEmbeddingClient
from app.config import get_settings
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
        embedding_vector = await embedding_client.embed(chunk_select['chunk'])
    print(f"selected chunks: {chunk_select['chunk']}")
    print(f"dimensions: {len(embedding_vector)}")
    print(f"first five elements: {embedding_vector[:5]}")

if __name__ == "__main__":
    asyncio.run(embedding_test())