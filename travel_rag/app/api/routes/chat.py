from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException, Request

from app.llm.client import ChatClient, ChatServiceError, ChatTimeoutError
from app.embeddings.client import EmbeddingClient,EmbeddingServiceError, EmbeddingTimeoutError
from app.schemas import AskResponse, ChatRequest, ChatResponse, TokenUsage
from app.rag.context_builder import builder_context
from app.rag.prompt_builder import build_prompt
from app.retrieval.retriever import find_most_similar_chunks
from app.rag.response_formatter import build_citation_response_obj, build_retrieved_response_obj, chat_refused_response_flag

router = APIRouter()


def get_chat_client(request: Request) -> ChatClient:
    return request.app.state.chat_client

def get_embedding_client(request: Request) -> EmbeddingClient:
    return request.app.state.embedding_client


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

@router.post("/ask", response_model=AskResponse, tags=["chat"])
async def ask(
    chat_request: ChatRequest,
    request: Request,
    chat_client: ChatClient = Depends(get_chat_client),
    embedding_client: EmbeddingClient = Depends(get_embedding_client),
) -> AskResponse:
    request_id: str = request.state.request_id
    started_at = perf_counter()

    try:
        embedded_question_vector = await embedding_client.embed(chat_request.question)
        top_matching_results = find_most_similar_chunks(embedded_question_vector, top_k=10)
        if top_matching_results["ids"][0] == []:
            return AskResponse(
                    answer="not enough policy evidence to answer that",
                    citations=[],
                    retrieved=[],
                    refused=True,
                    request_id=request_id,
                    latency_ms=round((perf_counter() - started_at) * 1000, 2),
                    token_usage=TokenUsage(
                        prompt_tokens=None,
                        completion_tokens=None,
                    ),
                )
        chat_context= builder_context(top_matching_results)
        prompt = build_prompt(chat_request.question, chat_context)
        result= await chat_client.generate(prompt)
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
    except EmbeddingTimeoutError as error:
            raise HTTPException(
                status_code=504,
                detail={"message": str(error), "request_id": request_id},
            ) from error
    except EmbeddingServiceError as error:
            raise HTTPException(
                status_code=502,
                detail={"message": str(error), "request_id": request_id},
            ) from error
    return AskResponse(
        answer = result.answer,
        citations = build_citation_response_obj(answer=result.answer, retrieved_chunks=top_matching_results),
        retrieved = build_retrieved_response_obj(retrieved_chunks=top_matching_results),
        refused = chat_refused_response_flag(answer=result.answer),
        request_id = request_id,
        latency_ms = round((perf_counter() - started_at) * 1000, 2),
        token_usage = TokenUsage(
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
        ),
    )
 