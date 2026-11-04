import asyncio

import httpx2
import pytest

from app.embeddings.client import (
    EmbeddingServiceError,
    EmbeddingTimeoutError,
    OllamaEmbeddingClient,
)


def test_embedding_client_posts_text_and_returns_vector() -> None:
    def handle_request(request: httpx2.Request) -> httpx2.Response:
        assert request.url.path == "/api/embed"
        assert request.read() == (
            b'{"model":"nomic-embed-text","input":"policy text"}'
        )
        return httpx2.Response(200, json={"embeddings": [[0.1, 0.2, 0.3]]})

    async def run() -> list[float]:
        async with httpx2.AsyncClient(
            transport=httpx2.MockTransport(handle_request),
        ) as http_client:
            client = OllamaEmbeddingClient(http_client, "nomic-embed-text")
            return await client.embed("policy text")

    assert asyncio.run(run()) == [0.1, 0.2, 0.3]


def test_embedding_client_maps_timeout() -> None:
    def handle_request(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ReadTimeout("timed out", request=request)

    async def run() -> None:
        async with httpx2.AsyncClient(
            transport=httpx2.MockTransport(handle_request),
        ) as http_client:
            client = OllamaEmbeddingClient(http_client, "nomic-embed-text")
            await client.embed("policy text")

    with pytest.raises(EmbeddingTimeoutError):
        asyncio.run(run())


@pytest.mark.parametrize(
    "response",
    [
        httpx2.Response(502),
        httpx2.Response(200, json={"unexpected": []}),
        httpx2.Response(200, json={"embeddings": []}),
        httpx2.Response(200, json={"embeddings": [[]]}),
    ],
)
def test_embedding_client_rejects_failed_or_invalid_responses(
    response: httpx2.Response,
) -> None:
    async def run() -> None:
        async with httpx2.AsyncClient(
            transport=httpx2.MockTransport(lambda request: response),
        ) as http_client:
            client = OllamaEmbeddingClient(http_client, "nomic-embed-text")
            await client.embed("policy text")

    with pytest.raises(EmbeddingServiceError):
        asyncio.run(run())


def test_embedding_client_rejects_blank_text_without_request() -> None:
    def handle_request(request: httpx2.Request) -> httpx2.Response:
        pytest.fail("blank text should not be sent")

    async def run() -> None:
        async with httpx2.AsyncClient(
            transport=httpx2.MockTransport(handle_request),
        ) as http_client:
            client = OllamaEmbeddingClient(http_client, "nomic-embed-text")
            await client.embed("  ")

    with pytest.raises(ValueError, match="text must not be empty"):
        asyncio.run(run())
