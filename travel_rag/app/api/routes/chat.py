from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException, Request

from app.llm.client import ChatClient, ChatServiceError, ChatTimeoutError
from app.schemas import ChatRequest, ChatResponse, TokenUsage

router = APIRouter()


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

@router.get("/ask", tags=["chat"])
async def ask(
    question: str,
    request: Request,
    chat_client: ChatClient = Depends(get_chat_client),
) -> ChatResponse:
    {}
