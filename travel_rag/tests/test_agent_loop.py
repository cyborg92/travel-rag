import asyncio
from datetime import datetime, timedelta

from app.agent.loop import (
    DEADLINE_SECONDS,
    HAS_CALLED_TOOL_ANSWER,
    MAX_TOOL_CALLS,
    MAX_TOOL_CALLS_ANSWER,
    TIMEOUT_ANSWER,
    run_agent,
)
from tests.fakes import FakeModel, text_reply, tool_reply

NOW = datetime(2026, 11, 14, 10, 0, 0)


def fixed_clock() -> datetime:
    return NOW


def run(coro):
    return asyncio.run(coro)


def test_text_only_reply_is_returned_as_the_answer():
    model = FakeModel([text_reply("Hello there")])
    result = run(run_agent("hi", "user-1", model, clock=fixed_clock))
    assert result.answer == "Hello there"
    assert result.stop_reason == "answered"
    assert result.tool_calls == []


def test_model_is_sent_system_prompt_with_clock_date_then_the_question():
    model = FakeModel([text_reply("ok")])
    run(run_agent("What is my fare?", "user-1", model, clock=fixed_clock))
    sent = model.calls[0]
    assert sent[0]["role"] == "system"
    assert "2026-11-14" in sent[0]["content"]
    assert sent[1] == {"role": "user", "content": "What is my fare?"}
    assert len(sent) == 2


def test_tool_request_is_executed_and_result_shown_to_the_model():
    model = FakeModel([
        tool_reply("get_booking", {"reference": "PNR001"}),
        text_reply("Your booking is confirmed."),
    ])
    result = run(run_agent("show PNR001", "user-1", model, clock=fixed_clock))

    assert result.answer == "Your booking is confirmed."
    assert result.stop_reason == "answered"
    assert [c.name for c in result.tool_calls] == ["get_booking"]
    assert "PNR001" in result.tool_calls[0].result

    second_call_messages = model.calls[1]
    assert second_call_messages[-1]["role"] == "tool"
    assert second_call_messages[-1]["content"] == result.tool_calls[0].result


def test_two_tools_in_one_reply_run_before_the_model_is_asked_again():
    two_calls = {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {"function": {"name": "get_booking", "arguments": {"reference": "PNR001"}}},
            {"function": {"name": "get_booking", "arguments": {"reference": "PNR006"}}},
        ],
    }
    model = FakeModel([two_calls, text_reply("Both found.")])
    result = run(run_agent("show both", "user-1", model, clock=fixed_clock))

    assert result.answer == "Both found."
    assert len(model.calls) == 2  # asked again once, not once per tool
    assert len(result.tool_calls) == 2
    tool_messages = [m for m in model.calls[1] if m["role"] == "tool"]
    assert len(tool_messages) == 2


def test_tool_failure_becomes_an_observation_the_model_can_read():
    model = FakeModel([
        tool_reply("get_booking", {"reference": "PNR999"}),
        text_reply("I could not find that booking."),
    ])
    result = run(run_agent("show PNR999", "user-1", model, clock=fixed_clock))

    assert result.answer == "I could not find that booking."
    assert "No booking found" in model.calls[1][-1]["content"]


def test_tool_call_runs_as_the_given_user_not_a_model_supplied_one():
    model = FakeModel([
        tool_reply("get_booking", {"reference": "PNR001"}),
        text_reply("done"),
    ])
    result = run(run_agent("show PNR001", "someone-else", model, clock=fixed_clock))
    assert "No booking found" in result.tool_calls[0].result


def test_model_can_use_tools_over_several_rounds():
    model = FakeModel([
        tool_reply("get_booking", {"reference": "PNR001"}),
        tool_reply("get_fare_rules", {"reference": "PNR001"}),
        text_reply("Here are the rules."),
    ])
    result = run(run_agent("rules for PNR001?", "user-1", model, clock=fixed_clock))

    assert result.answer == "Here are the rules."
    assert result.stop_reason == "answered"
    assert [c.name for c in result.tool_calls] == ["get_booking", "get_fare_rules"]
    assert len(model.calls) == 3


def test_each_round_sees_the_results_of_earlier_rounds():
    model = FakeModel([
        tool_reply("get_booking", {"reference": "PNR001"}),
        tool_reply("get_fare_rules", {"reference": "PNR001"}),
        text_reply("done"),
    ])
    run(run_agent("go", "user-1", model, clock=fixed_clock))

    roles_third_call = [m["role"] for m in model.calls[2]]
    assert roles_third_call == ["system", "user", "assistant", "tool", "assistant", "tool"]


def distinct_booking_calls(count: int) -> list[dict]:
    """tool replies with different arguments each time, so no duplicate guard fires"""
    return [tool_reply("get_booking", {"reference": f"PNR00{i}"}) for i in range(1, count + 1)]


def test_stops_after_max_tool_calls_when_model_never_answers():
    model = FakeModel(distinct_booking_calls(MAX_TOOL_CALLS + 1))
    result = run(run_agent("loop forever", "user-1", model, clock=fixed_clock))

    assert result.stop_reason == "too_many_calls"
    assert result.answer == MAX_TOOL_CALLS_ANSWER
    assert len(result.tool_calls) == MAX_TOOL_CALLS
    assert len(model.calls) == MAX_TOOL_CALLS + 1  # never asked after the limit hit


def test_exactly_max_tool_calls_then_an_answer_is_not_stopped():
    replies = distinct_booking_calls(MAX_TOOL_CALLS) + [text_reply("finished")]
    model = FakeModel(replies)
    result = run(run_agent("five calls", "user-1", model, clock=fixed_clock))

    assert result.stop_reason == "answered"
    assert result.answer == "finished"
    assert len(result.tool_calls) == MAX_TOOL_CALLS


def test_limit_applies_within_a_single_reply_with_many_requests():
    many = {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {"function": {"name": "get_booking", "arguments": {"reference": f"PNR00{i}"}}}
            for i in range(1, MAX_TOOL_CALLS + 3)
        ],
    }
    model = FakeModel([many])
    result = run(run_agent("many at once", "user-1", model, clock=fixed_clock))

    assert result.stop_reason == "too_many_calls"
    assert len(result.tool_calls) == MAX_TOOL_CALLS


def test_identical_call_is_skipped_and_only_runs_once():
    same = tool_reply("get_booking", {"reference": "PNR001"})
    model = FakeModel([same, same, text_reply("done")])
    result = run(run_agent("repeat", "user-1", model, clock=fixed_clock))

    assert result.stop_reason == "answered"
    assert len(result.tool_calls) == 1  # the repeat was never executed


def test_model_is_told_when_a_call_was_skipped_as_a_duplicate():
    same = tool_reply("get_booking", {"reference": "PNR001"})
    model = FakeModel([same, same, text_reply("done")])
    run(run_agent("repeat", "user-1", model, clock=fixed_clock))

    last_tool_message = model.calls[2][-1]
    assert last_tool_message["role"] == "tool"
    assert last_tool_message["content"] == HAS_CALLED_TOOL_ANSWER


def test_duplicate_with_reordered_arguments_is_still_skipped():
    first = tool_reply("quote_change", {"reference": "PNR001", "new_date": "2026-11-21"})
    second = tool_reply("quote_change", {"new_date": "2026-11-21", "reference": "PNR001"})
    model = FakeModel([first, second, text_reply("done")])
    result = run(run_agent("quote", "user-1", model, clock=fixed_clock))

    assert len(result.tool_calls) == 1


def test_same_tool_with_different_arguments_is_not_a_duplicate():
    model = FakeModel([
        tool_reply("get_booking", {"reference": "PNR001"}),
        tool_reply("get_booking", {"reference": "PNR006"}),
        text_reply("done"),
    ])
    result = run(run_agent("two bookings", "user-1", model, clock=fixed_clock))

    assert len(result.tool_calls) == 2


def test_skipped_duplicates_do_not_use_up_the_call_budget():
    same = tool_reply("get_booking", {"reference": "PNR001"})
    model = FakeModel([same] * 8 + [text_reply("done")])
    result = run(run_agent("repeat a lot", "user-1", model, clock=fixed_clock))

    assert result.stop_reason == "answered"
    assert len(result.tool_calls) == 1


class SteppingClock:
    """Returns the given times in order, then keeps returning the last one."""

    def __init__(self, *times: datetime) -> None:
        self._times = list(times)
        self.reads = 0

    def __call__(self) -> datetime:
        index = min(self.reads, len(self._times) - 1)
        self.reads += 1
        return self._times[index]


def at(seconds: int) -> datetime:
    return NOW + timedelta(seconds=seconds)


def test_stops_with_timeout_once_the_deadline_has_passed():
    clock = SteppingClock(at(0), at(10), at(DEADLINE_SECONDS + 10))
    model = FakeModel(distinct_booking_calls(4))
    result = run(run_agent("slow", "user-1", model, clock=clock))

    assert result.stop_reason == "timeout"
    assert result.answer == TIMEOUT_ANSWER
    assert len(result.tool_calls) == 1  # round 1 ran in time, round 2 was refused
    assert len(model.calls) == 2


def test_exactly_at_the_deadline_is_still_allowed():
    clock = SteppingClock(at(0), at(DEADLINE_SECONDS))
    model = FakeModel([tool_reply("get_booking", {"reference": "PNR001"}), text_reply("done")])
    result = run(run_agent("on the line", "user-1", model, clock=clock))

    assert result.stop_reason == "answered"


def test_deadline_stops_a_model_that_only_repeats_itself():
    same = tool_reply("get_booking", {"reference": "PNR001"})
    clock = SteppingClock(at(0), at(5), at(15), at(25), at(DEADLINE_SECONDS + 5))
    model = FakeModel([same] * 6)
    result = run(run_agent("endless repeat", "user-1", model, clock=clock))

    assert result.stop_reason == "timeout"
    assert len(result.tool_calls) == 1  # duplicates never reached the call limit


def test_fast_runs_never_trigger_the_deadline():
    model = FakeModel([tool_reply("get_booking", {"reference": "PNR001"}), text_reply("done")])
    result = run(run_agent("quick", "user-1", model, clock=fixed_clock))

    assert result.stop_reason == "answered"
