from time import perf_counter
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from app.llm.client import ChatClient, ChatServiceError, ChatTimeoutError
from app.schemas import ChatRequest, ChatResponse, TokenUsage

router = APIRouter()


@router.get("/", tags=["operations"])
def root() -> PlainTextResponse:
    return PlainTextResponse("server is running")


def get_chat_client(request: Request) -> ChatClient:
    return request.app.state.chat_client


@router.post("/chat", response_model=ChatResponse, tags=["chat"])
async def chat(
    chat_request: ChatRequest,
    request: Request,
    chat_client: ChatClient = Depends(get_chat_client),
) -> ChatResponse:
    request_id: str = request.state.request_id
    started_at = perf_counter()

    try:
        result = await chat_client.generate(chat_request.question)
    except ChatTimeoutError as error:
        raise HTTPException(
            status_code=504,
            detail={"message": str(error), "request_id": request_id},
        ) from error
    except ChatServiceError as error:
        raise HTTPException(
            status_code=502,
            detail={"message": str(error), "request_id": request_id},
        ) from error

    return ChatResponse(
        answer=result.answer,
        request_id=request_id,
        latency_ms=round((perf_counter() - started_at) * 1000, 2),
        token_usage=TokenUsage(
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
        ),
    )


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str


@router.get("/health", response_model=HealthResponse, tags=["operations"])
def health_check() -> HealthResponse:
    return HealthResponse(status="ok", service="travel-rag")
