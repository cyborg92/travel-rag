from app.retrieval import retriever


class FakeCollection:
    def __init__(self) -> None:
        self.query_arguments: dict | None = None

    def query(self, **kwargs) -> dict:
        self.query_arguments = kwargs
        return {"ids": [["policy.md:0"]]}


def test_find_most_similar_chunks_queries_chroma_with_vector_and_top_k(
    monkeypatch,
) -> None:
    fake_collection = FakeCollection()
    monkeypatch.setattr(retriever, "collection", fake_collection)

    result = retriever.find_most_similar_chunks([0.1, 0.2], top_k=3)

    assert result == {"ids": [["policy.md:0"]]}
    assert fake_collection.query_arguments == {
        "query_embeddings": [[0.1, 0.2]],
        "n_results": 3,
        "include": ["metadatas", "documents", "distances"],
    }
