from typing import Protocol

import httpx2
from pydantic import BaseModel, ValidationError


class EmbeddingTimeoutError(Exception):
    pass


class EmbeddingServiceError(Exception):
    pass


class EmbeddingClient(Protocol):
    async def embed(self, text: str) -> list[float]: ...


class OllamaEmbeddingResponse(BaseModel):
    embeddings: list[list[float]]


class OllamaEmbeddingClient:
    def __init__(
        self,
        http_client: httpx2.AsyncClient,
        model: str,
    ) -> None:
        self._http_client = http_client
        self._model = model

    async def embed(self, text: str) -> list[float]:
        if not text.strip():
            raise ValueError("text must not be empty.")

        try:
            response = await self._http_client.post(
                "/api/embed",
                json={"model": self._model, "input": text},
            )
            response.raise_for_status()
            ollama_response = OllamaEmbeddingResponse.model_validate(response.json())
        except httpx2.TimeoutException as error:
            raise EmbeddingTimeoutError(
                "The embedding service timed out."
            ) from error
        except (httpx2.HTTPError, ValidationError, ValueError) as error:
            raise EmbeddingServiceError(
                "The embedding service request failed."
            ) from error

        if len(ollama_response.embeddings) != 1 or not ollama_response.embeddings[0]:
            raise EmbeddingServiceError(
                "The embedding service returned an invalid embedding."
            )
        return ollama_response.embeddings[0]
