from typing import Literal

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

router = APIRouter()


@router.get("/", tags=["operations"])
def root() -> PlainTextResponse:
    return PlainTextResponse("server is running")


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str


@router.get("/health", response_model=HealthResponse, tags=["operations"])
def health_check() -> HealthResponse:
    return HealthResponse(status="ok", service="travel-rag")
