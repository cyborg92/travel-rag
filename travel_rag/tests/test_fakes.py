import asyncio

import pytest

from tests.fakes import FakeModel, ScriptedModelExhausted, text_reply, tool_reply


def run(coro):
    return asyncio.run(coro)


def test_text_reply_has_no_tool_calls():
    reply = text_reply("hello")
    assert reply == {"role": "assistant", "content": "hello"}
    assert not reply.get("tool_calls")


def test_tool_reply_matches_ollama_shape():
    reply = tool_reply("get_booking", {"reference": "PNR001"})
    call = reply["tool_calls"][0]
    assert call["function"]["name"] == "get_booking"
    assert call["function"]["arguments"] == {"reference": "PNR001"}


def test_replies_come_back_in_order():
    model = FakeModel([tool_reply("get_booking", {"reference": "PNR001"}), text_reply("done")])
    assert run(model([]))["tool_calls"]
    assert run(model([]))["content"] == "done"


def test_records_messages_as_they_were_at_call_time():
    model = FakeModel([text_reply("a"), text_reply("b")])
    messages = [{"role": "user", "content": "hi"}]
    run(model(messages))
    messages.append({"role": "tool", "content": "later"})
    run(model(messages))
    assert len(model.calls[0]) == 1
    assert len(model.calls[1]) == 2


def test_running_out_of_replies_raises():
    model = FakeModel([text_reply("only one")])
    run(model([]))
    with pytest.raises(ScriptedModelExhausted):
        run(model([]))
