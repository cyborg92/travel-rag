from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    question: str = Field(min_length=1, max_length=2000)

class GroundedReply(BaseModel):
    status: Literal["answered", "insufficient_evidence"]
    answer: str

class TokenUsage(BaseModel):
    prompt_tokens: int | None
    completion_tokens: int | None


class ChatResponse(BaseModel):
    answer: str
    request_id: str
    latency_ms: float
    token_usage: TokenUsage

class AskResponse(BaseModel):
    answer: str
    citations: list[dict]
    retrieved: list[dict]
    refused: bool = False
    request_id: str
    latency_ms: float
    token_usage: TokenUsage
    
