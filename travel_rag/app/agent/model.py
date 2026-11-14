"""The chat-model function the agent loop calls.

The loop only needs one thing from a model: send these messages, get one reply
message back (which may contain `tool_calls`). Keeping that as a plain async
function lets tests substitute a scripted fake.
"""
from collections.abc import Awaitable, Callable

import httpx2

from app.tools.registry import TOOLS

# What the loop depends on: await ask_model(messages) -> reply message dict.
AskModel = Callable[[list[dict]], Awaitable[dict]]


def build_tool_definitions() -> list[dict]:
    """Tool descriptions in the format Ollama expects, built from the registry."""
    return [
        {
            "type": "function",
            "function": {
                "name": spec.name,
                "description": spec.description,
                "parameters": spec.args_model.model_json_schema(),
            },
        }
        for spec in TOOLS.values()
    ]


def make_ollama_model(http_client: httpx2.AsyncClient, model_name: str) -> AskModel:
    """Return an `ask_model` function bound to one HTTP client and model."""
    tools = build_tool_definitions()

    async def ask_model(messages: list[dict]) -> dict:
        response = await http_client.post(
            "/api/chat",
            json={
                "model": model_name,
                "messages": messages,
                "stream": False,
                "tools": tools,
            },
        )
        response.raise_for_status()
        return response.json()["message"]

    return ask_model
