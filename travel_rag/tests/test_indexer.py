import asyncio

from app.ingestion import indexer


class FakeEmbeddingClient:
    def __init__(self) -> None:
        self.texts: list[str] = []

    async def embed(self, text: str) -> list[float]:
        self.texts.append(text)
        return [0.1, 0.2]


def test_index_chunks_embeds_and_upserts_each_chunk(monkeypatch) -> None:
    embedding_client = FakeEmbeddingClient()
    upserted_chunks: list[dict] = []

    def fake_upsert_chunk(**kwargs) -> None:
        upserted_chunks.append(kwargs)

    monkeypatch.setattr(indexer, "upsert_chunk", fake_upsert_chunk)

    chunks = [
        {
            "source": "policy.md",
            "chunk_index": 0,
            "section": "Baggage",
            "chunk": "Cabin allowance",
        },
        {
            "source": "policy.md",
            "chunk_index": 1,
            "chunk": "Checked allowance",
        },
    ]

    indexed_count = asyncio.run(indexer.index_chunks(chunks, embedding_client))

    assert indexed_count == 2
    assert embedding_client.texts == ["Cabin allowance", "Checked allowance"]
    assert upserted_chunks == [
        {
            "embedding_vector": [0.1, 0.2],
            "text": "Cabin allowance",
            "stable_id": "policy.md:0",
            "metadata": {
                "source": "policy.md",
                "chunk_index": 0,
                "section": "Baggage",
            },
        },
        {
            "embedding_vector": [0.1, 0.2],
            "text": "Checked allowance",
            "stable_id": "policy.md:1",
            "metadata": {
                "source": "policy.md",
                "chunk_index": 1,
            },
        },
    ]
