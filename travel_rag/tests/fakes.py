"""Test doubles for the agent loop: a scripted stand-in for the chat model."""
from copy import deepcopy


def text_reply(content: str) -> dict:
    """A final answer with no tool calls, shaped like Ollama's message."""
    return {"role": "assistant", "content": content}


def tool_reply(name: str, arguments: dict) -> dict:
    """A reply that asks for one tool call, shaped like Ollama's message."""
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [{"function": {"name": name, "arguments": arguments}}],
    }


class ScriptedModelExhausted(AssertionError):
    """The loop asked for more replies than the test scripted."""


class FakeModel:
    """Returns scripted replies in order and records what it was sent.

    Same call shape as the real model function: await model(messages) -> dict.
    Running out of replies raises, so a loop that never stops fails the test
    instead of hanging it.
    """

    def __init__(self, replies: list[dict]) -> None:
        self._replies = list(replies)
        self.calls: list[list[dict]] = []

    async def __call__(self, messages: list[dict]) -> dict:
        # Snapshot: the loop keeps appending to the same list afterwards.
        self.calls.append(deepcopy(messages))
        if len(self.calls) > len(self._replies):
            raise ScriptedModelExhausted(
                f"model called {len(self.calls)} times, only {len(self._replies)} replies scripted"
            )
        return deepcopy(self._replies[len(self.calls) - 1])
