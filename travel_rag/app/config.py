from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TRAVEL_RAG_")

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_timeout_seconds: float = Field(default=60, gt=0)
    # Demo routes run deterministic code paths (no model) for showcasing. On by default; set TRAVEL_RAG_ENABLE_DEMO_ROUTES=false to hide them.
    enable_demo_routes: bool = True
    # The demo agent route calls a live model (slow, varies per run), so it has its own flag. On by default; set TRAVEL_RAG_ENABLE_DEMO_AGENT=false to hide it.
    enable_demo_agent: bool = True
    demo_agent_max_runs_per_minute: int = Field(default=6, gt=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
