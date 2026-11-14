"""Send one raw chat request straight to Ollama and print the full response.

Used to look at what the model actually returns (for example `tool_calls`)
without the FastAPI server or the chat client wrapper in the way. Run from
travel_rag/:
    ./.venv/bin/python -m scripts.ollama_tools_experiment_script
"""
import asyncio
import httpx2
import json
from app.config import get_settings
from app.agent.model import make_ollama_model
from app.agent.loop import run_agent

QUESTION = "What would it cost to move PNR001 and PNR006 to 2026-12-12?"

CURRENT_USER = "user-1"

async def agent_endpoint_testing() -> None:
    settings = get_settings()
    async with httpx2.AsyncClient(
        base_url=settings.ollama_base_url,
        timeout=settings.ollama_timeout_seconds,
    ) as http_client:
        try:
            ask_model = make_ollama_model(http_client, settings.ollama_model)
            result = await run_agent(QUESTION, CURRENT_USER, ask_model)
            print (f"the answer → {result.answer}")
            print (f"the stop reason → {result.stop_reason}")
            for record in result.tool_calls: 
                print (f"the tool name → {record.name}")
                print (f"the tool arguments → {record.arguments}")
        except httpx2.TimeoutException:
            print("Ollama timed out.")
            return
        except httpx2.HTTPError as error:
            print(f"Ollama request failed: {error}")
            return

if __name__ == "__main__":
    asyncio.run(agent_endpoint_testing())
