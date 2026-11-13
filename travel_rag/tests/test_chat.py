from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.routes.chat import get_chat_client, get_embedding_client
from app.llm.client import ChatResult, ChatServiceError, ChatTimeoutError
from app.main import app


class FakeChatClient:
    def __init__(self) -> None:
        self.question: str | None = None
        self.error: Exception | None = None
        self.answer = "Check the applicable travel policy."
        self.status = "answered"

    async def generate(self, question: str) -> ChatResult:
        self.question = question
        if self.error is not None:
            raise self.error
        return ChatResult(
            answer=self.answer,
            prompt_tokens=12,
            completion_tokens=8,
        )

    async def generate_ground_prompt(self, question: str) -> ChatResult:
        result = await self.generate(question)
        return ChatResult(
            answer=result.answer,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            status=self.status,
        )


class FakeEmbeddingClient:
    async def embed(self, question: str) -> list[float]:
        return [0.1, 0.2]


@pytest.fixture
def fake_chat_client() -> FakeChatClient:
    return FakeChatClient()


@pytest.fixture
def client(fake_chat_client: FakeChatClient) -> Iterator[TestClient]:
    app.dependency_overrides[get_chat_client] = lambda: fake_chat_client
    app.dependency_overrides[get_embedding_client] = FakeEmbeddingClient
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_chat_returns_answer_request_id_latency_and_token_usage(
    client: TestClient,
    fake_chat_client: FakeChatClient,
) -> None:
    response = client.post("/chat", json={"question": "What is the baggage policy?"})
    body = response.json()

    assert response.status_code == 200
    assert set(body) == {"answer", "request_id", "latency_ms", "token_usage"}
    assert body["answer"] == "Check the applicable travel policy."
    assert body["request_id"] == response.headers["x-request-id"]
    assert body["token_usage"] == {"prompt_tokens": 12, "completion_tokens": 8}
    assert isinstance(body["latency_ms"], (int, float))
    assert body["latency_ms"] >= 0
    assert fake_chat_client.question == "What is the baggage policy?"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"question": ""},
        {"question": "   "},
        {"question": "x" * 2001},
        {"question": "valid question", "unexpected": True},
    ],
)
def test_chat_rejects_invalid_request(
    client: TestClient,
    fake_chat_client: FakeChatClient,
    payload: dict[str, object],
) -> None:
    response = client.post("/chat", json=payload)

    assert response.status_code == 422
    assert response.json()["request_id"] == response.headers["x-request-id"]
    assert fake_chat_client.question is None


def test_chat_maps_upstream_failure_to_502_with_request_id(
    client: TestClient,
    fake_chat_client: FakeChatClient,
) -> None:
    fake_chat_client.error = ChatServiceError("The chat service request failed.")

    response = client.post("/chat", json={"question": "Ask a question"})

    assert response.status_code == 502
    assert response.json()["detail"]["request_id"] == response.headers["x-request-id"]


def test_chat_maps_timeout_to_504_with_request_id(
    client: TestClient,
    fake_chat_client: FakeChatClient,
) -> None:
    fake_chat_client.error = ChatTimeoutError("The chat service timed out.")

    response = client.post("/chat", json={"question": "Ask a question"})

    assert response.status_code == 504
    assert response.json()["detail"]["request_id"] == response.headers["x-request-id"]


def test_ask_maps_answer_citations_to_retrieved_chunk_metadata(
    client: TestClient,
    fake_chat_client: FakeChatClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.api.routes import chat as chat_routes

    retrieved_chunks = {
        "ids": [["baggage.md:2", "baggage.md:3"]],
        "documents": [["Cabin baggage.", "Checked baggage."]],
        "metadatas": [[
            {"source": "baggage.md", "section": "Cabin baggage", "chunk_index": 2},
            {"source": "baggage.md", "section": "Checked baggage", "chunk_index": 3},
        ]],
        "distances": [[0.4, 0.6]],
    }
    monkeypatch.setattr(
        chat_routes,
        "find_most_similar_chunks",
        lambda _vector, top_k: retrieved_chunks,
    )
    fake_chat_client.answer = "See [Source 2 | File: wrong.md] for the limit."

    response = client.post("/ask", json={"question": "What is the limit?"})
    body = response.json()

    assert response.status_code == 200
    assert body["answer"] == "See [Source 2 | File: wrong.md] for the limit."
    assert body["citations"] == [
        {
            "label": "Source 2",
            "id": "baggage.md:3",
            "source": "baggage.md",
            "section": "Checked baggage",
            "chunk_index": 3,
        }
    ]
    assert body["retrieved"] == [
        {"id": "baggage.md:2", "distance": 0.4},
        {"id": "baggage.md:3", "distance": 0.6},
    ]
    assert body["refused"] is False


def test_ask_refuses_without_calling_chat_when_retrieval_is_empty(
    client: TestClient,
    fake_chat_client: FakeChatClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.api.routes import chat as chat_routes

    monkeypatch.setattr(
        chat_routes,
        "find_most_similar_chunks",
        lambda _vector, top_k: {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        },
    )

    response = client.post("/ask", json={"question": "Unknown policy question"})
    body = response.json()

    assert response.status_code == 200
    assert body["refused"] is True
    assert body["citations"] == []
    assert body["retrieved"] == []
    assert fake_chat_client.question is None


def test_ask_sets_refused_from_structured_status_not_answer_text(
    client: TestClient,
    fake_chat_client: FakeChatClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.api.routes import chat as chat_routes

    monkeypatch.setattr(
        chat_routes,
        "find_most_similar_chunks",
        lambda _vector, top_k: {
            "ids": [["baggage.md:2"]],
            "documents": [["text"]],
            "metadatas": [[{"source": "baggage.md", "section": "Cabin baggage", "chunk_index": 2}]],
            "distances": [[0.4]],
        },
    )
    # Declined in the model's own words, without any magic phrase.
    fake_chat_client.answer = "That topic is not covered by these documents."
    fake_chat_client.status = "insufficient_evidence"

    body = client.post("/ask", json={"question": "Can I bring a pet?"}).json()

    assert body["refused"] is True
