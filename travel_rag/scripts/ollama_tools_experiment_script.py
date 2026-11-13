"""Send one raw chat request straight to Ollama and print the full response.

Used to look at what the model actually returns (for example `tool_calls`)
without the FastAPI server or the chat client wrapper in the way. Run from
travel_rag/:
    ./.venv/bin/python -m scripts.ollama_tools_experiment_script
"""
import asyncio
import json
from datetime import datetime

import httpx2

from app.agent.prompts import build_system_prompt
from app.config import get_settings
from app.tools.executor import execute_tool
from app.tools.registry import TOOLS

QUESTION = "What would it cost to move PNR001 and PNR006 to 2026-12-12?"

tools = [
    {"type": "function", "function": {
        "name": spec.name,
        "description": spec.description,
        "parameters": spec.args_model.model_json_schema(),
    }}
    for spec in TOOLS.values()
]
CURRENT_USER = "user-1"

async def ask_ollama(http_client,messages_arr) -> dict:
    settings = get_settings()
    request_body = {
               "model": settings.ollama_model,
               "messages": messages_arr,
               "stream": False,
               "tools": tools
    }
    response = await http_client.post("/api/chat", json=request_body)
    response.raise_for_status()
    return response.json()["message"]

async def chat_endpoint_testing() -> None:
    messages = [
        {"role": "system", "content": build_system_prompt(datetime.now())},
        {"role": "user", "content": QUESTION},
    ]
    settings = get_settings()
    async with httpx2.AsyncClient(
        base_url=settings.ollama_base_url,
        timeout=settings.ollama_timeout_seconds,
        ) as http_client:
        try:
            reply_1 = await ask_ollama(http_client, messages)
            messages.append(reply_1)
            tool_calls = reply_1.get("tool_calls") or []
            if tool_calls:
                for call in tool_calls:
                    tool_fnc, tool_args= call["function"]["name"], call["function"]["arguments"]
                    observation = execute_tool(tool_fnc, tool_args,CURRENT_USER)
                    messages.append({"role": "tool", "content": observation})
                reply_2 = await ask_ollama(http_client, messages)
                messages.append(reply_2)
        except httpx2.TimeoutException:
            print("Ollama timed out.")
            return
        except httpx2.HTTPError as error:
            print(f"Ollama request failed: {error}")
            return

    print(json.dumps(messages, indent=2))


if __name__ == "__main__":
    asyncio.run(chat_endpoint_testing())
