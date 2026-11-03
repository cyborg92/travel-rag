from dataclasses import dataclass
from typing import Protocol

import httpx2
from pydantic import BaseModel, ValidationError


class ChatTimeoutError(Exception):
    pass


class ChatServiceError(Exception):
    pass


@dataclass(frozen=True)
class ChatResult:
    answer: str
    prompt_tokens: int | None
    completion_tokens: int | None


class ChatClient(Protocol):
    async def generate(self, question: str) -> ChatResult: ...


class OllamaMessage(BaseModel):
    content: str


class OllamaChatResponse(BaseModel):
    message: OllamaMessage
    prompt_eval_count: int | None = None
    eval_count: int | None = None


class OllamaChatClient:
    def __init__(self, http_client: httpx2.AsyncClient, model: str) -> None:
        self._http_client = http_client
        self._model = model

    async def generate(self, question: str) -> ChatResult:
        try:
            response = await self._http_client.post(
                "/api/chat",
                json={
                    "model": self._model,
                    "messages": [{"role": "user", "content": question}],
                    "stream": False,
                },
            )
            response.raise_for_status()
            ollama_response = OllamaChatResponse.model_validate(response.json())
        except httpx2.TimeoutException as error:
            raise ChatTimeoutError("The chat service timed out.") from error
        except (httpx2.HTTPError, ValidationError, ValueError) as error:
            raise ChatServiceError("The chat service request failed.") from error

        return ChatResult(
            answer=ollama_response.message.content,
            prompt_tokens=ollama_response.prompt_eval_count,
            completion_tokens=ollama_response.eval_count,
        )
