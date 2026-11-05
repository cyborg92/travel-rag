from typing import Literal

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from app.ingestion.chunker import chunk_section
from app.ingestion.doc_reader import load_documents

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


@router.get("/chunkertest", tags=["operations"])
def chunker_test() -> PlainTextResponse:
    docs = load_documents()
    chunk_details = []
    for filename, text in docs:
        chunks = chunk_section(text, filename)
        chunk_details.append(f"{filename}: {len(chunks)} chunks")
        for index, chunk in enumerate(chunks, start=1):
            chunk_details.append(f"Chunk {index}:\n{chunk}")
    return PlainTextResponse("\n".join(chunk_details))
