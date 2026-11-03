from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.routes import get_chat_client
from app.llm.client import ChatResult, ChatServiceError, ChatTimeoutError
from app.main import app


class FakeChatClient:
    def __init__(self) -> None:
        self.question: str | None = None
        self.error: Exception | None = None

    async def generate(self, question: str) -> ChatResult:
        self.question = question
        if self.error is not None:
            raise self.error
        return ChatResult(
            answer="Check the applicable travel policy.",
            prompt_tokens=12,
            completion_tokens=8,
        )


@pytest.fixture
def fake_chat_client() -> FakeChatClient:
    return FakeChatClient()


@pytest.fixture
def client(fake_chat_client: FakeChatClient) -> Iterator[TestClient]:
    app.dependency_overrides[get_chat_client] = lambda: fake_chat_client
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
