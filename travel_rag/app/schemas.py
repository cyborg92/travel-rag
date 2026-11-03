from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    question: str = Field(min_length=1, max_length=2000)


class TokenUsage(BaseModel):
    prompt_tokens: int | None
    completion_tokens: int | None


class ChatResponse(BaseModel):
    answer: str
    request_id: str
    latency_ms: float
    token_usage: TokenUsage
