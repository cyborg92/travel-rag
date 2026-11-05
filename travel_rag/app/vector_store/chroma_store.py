from pathlib import Path

import chromadb

database_path = Path(__file__).resolve().parents[2] / ".chroma_db"
print(f"Database path: {database_path}")
client = chromadb.PersistentClient(path=str(database_path))

collection = client.get_or_create_collection("travel_rag_collection")

def upsert_chunk(
    embedding_vector: list[float],
    text: str,
    stable_id: str,
    metadata: dict[str, str | int],
) -> dict[str, list]:
    """
    Insert or replace a chunk and return the stored document and metadata.
    """
    collection.upsert(
        ids=[stable_id],
        embeddings=[embedding_vector],
        documents=[text],
        metadatas=[metadata],
    )
    return collection.get(
        ids=[stable_id],
        include=["documents", "metadatas"],
    )