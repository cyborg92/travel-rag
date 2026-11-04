from contextlib import asynccontextmanager
from typing import AsyncGenerator
from uuid import uuid4

import httpx2
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from app.config import get_settings
from app.api.routes import router
from app.llm.client import OllamaChatClient

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    async with httpx2.AsyncClient(
        base_url=settings.ollama_base_url,
        timeout=settings.ollama_timeout_seconds,
    ) as http_client:
        app.state.chat_client = OllamaChatClient(http_client, settings.ollama_model)
        yield

app = FastAPI(
    title="Travel Assistant API",
    description="A learning project for a travel knowledge assistant powered by RAG.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.middleware("http")
async def add_request_id(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    request_id = str(uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "detail": jsonable_encoder(error.errors()),
            "request_id": request.state.request_id,
        },
    )

