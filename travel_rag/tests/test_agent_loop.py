import asyncio
import logging
from datetime import datetime, timedelta

from app.agent.loop import (
    DEADLINE_SECONDS,
    HAS_CALLED_TOOL_ANSWER,
    MAX_TOOL_CALLS,
    CONFIRMED_HEADER,
    MAX_TOOL_CALLS_ANSWER,
    PREFIX,
    SEPARATOR,
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


def messages_logged(caplog) -> list[str]:
    return [record.getMessage() for record in caplog.records if record.name == "app.agent.loop"]


def test_trace_records_each_tool_run_and_the_final_answer(caplog):
    caplog.set_level(logging.INFO, logger="app.agent.loop")
    model = FakeModel([tool_reply("get_booking", {"reference": "PNR001"}), text_reply("done")])
    run(run_agent("trace me", "user-1", model, clock=fixed_clock))

    logged = messages_logged(caplog)
    assert any("agent tool: get_booking" in line for line in logged)
    assert any("answered after 1 tool calls" in line for line in logged)


def test_trace_records_a_skipped_duplicate(caplog):
    caplog.set_level(logging.INFO, logger="app.agent.loop")
    same = tool_reply("get_booking", {"reference": "PNR001"})
    model = FakeModel([same, same, text_reply("done")])
    run(run_agent("repeat", "user-1", model, clock=fixed_clock))

    assert any("skip duplicate" in line for line in messages_logged(caplog))


def test_trace_records_why_a_run_was_stopped(caplog):
    caplog.set_level(logging.INFO, logger="app.agent.loop")
    run(run_agent("limit", "user-1", FakeModel(distinct_booking_calls(MAX_TOOL_CALLS + 1)), clock=fixed_clock))
    assert any("too_many_calls" in line for line in messages_logged(caplog))

    caplog.clear()
    clock = SteppingClock(at(0), at(DEADLINE_SECONDS + 5))
    run(run_agent("slow", "user-1", FakeModel(distinct_booking_calls(2)), clock=clock))
    assert any("timeout" in line for line in messages_logged(caplog))


def test_trace_does_not_contain_tool_results(caplog):
    caplog.set_level(logging.DEBUG, logger="app.agent.loop")
    model = FakeModel([tool_reply("get_booking", {"reference": "PNR001"}), text_reply("done")])
    run(run_agent("privacy", "user-1", model, clock=fixed_clock))

    assert not any("Demo Passenger" in line for line in messages_logged(caplog))


QUOTE_PNR001 = tool_reply("quote_change", {"reference": "PNR001", "new_date": "2026-12-12"})


def test_missing_credit_is_appended_to_the_final_answer():
    model = FakeModel([QUOTE_PNR001, text_reply("Fee 3,500 INR. Tax difference is not included.")])
    result = run(run_agent("quote", "user-1", model, clock=fixed_clock))

    assert result.stop_reason == "answered"
    assert result.answer.startswith("Fee 3,500 INR. Tax difference is not included.")
    assert PREFIX + "Travel credit of ₹700, valid for 12 months" in result.answer


def test_missing_note_is_appended_to_the_final_answer():
    model = FakeModel([QUOTE_PNR001, text_reply("Fee 3,500 INR and a 700 INR credit.")])
    result = run(run_agent("quote", "user-1", model, clock=fixed_clock))

    assert PREFIX + "Tax difference is not included." in result.answer


def test_several_missing_facts_are_joined_in_one_line():
    model = FakeModel([QUOTE_PNR001, text_reply("It costs 3,500 INR.")])
    result = run(run_agent("quote", "user-1", model, clock=fixed_clock))

    missing_line = result.answer.split("\n\n")[1]
    assert missing_line == PREFIX + SEPARATOR.join(
        ["Tax difference is not included.", "Travel credit of ₹700, valid for 12 months"]
    )


def test_complete_answer_gets_no_missing_facts_line():
    complete = "Fee 3,500 INR, 700 INR credit valid 12 months. Tax difference is not included."
    model = FakeModel([QUOTE_PNR001, text_reply(complete)])
    result = run(run_agent("quote", "user-1", model, clock=fixed_clock))

    assert result.answer.startswith(complete)
    assert PREFIX not in result.answer


def test_answer_with_no_tool_calls_is_never_extended():
    model = FakeModel([text_reply("Hello")])
    result = run(run_agent("hi", "user-1", model, clock=fixed_clock))

    assert result.answer == "Hello"


def test_a_failed_tool_does_not_add_facts():
    model = FakeModel([tool_reply("get_booking", {"reference": "PNR999"}), text_reply("Not found.")])
    result = run(run_agent("find", "user-1", model, clock=fixed_clock))

    assert result.answer == "Not found."


def test_guard_stops_return_their_fixed_message_without_added_facts():
    model = FakeModel([QUOTE_PNR001] + distinct_booking_calls(MAX_TOOL_CALLS + 1))
    result = run(run_agent("limit", "user-1", model, clock=fixed_clock))

    assert result.stop_reason == "too_many_calls"
    assert result.answer == MAX_TOOL_CALLS_ANSWER


def test_missing_facts_are_logged(caplog):
    caplog.set_level(logging.INFO, logger="app.agent.loop")
    model = FakeModel([QUOTE_PNR001, text_reply("Fee 3,500 INR.")])
    run(run_agent("quote", "user-1", model, clock=fixed_clock))

    assert any("facts missing from answer" in line for line in messages_logged(caplog))


def test_facts_from_every_quote_are_checked_against_the_one_answer():
    quote_006 = tool_reply("quote_change", {"reference": "PNR006", "new_date": "2026-12-12"})
    model = FakeModel([QUOTE_PNR001, quote_006, text_reply("Both cost money.")])
    result = run(run_agent("both", "user-1", model, clock=fixed_clock))

    assert result.answer.count("Tax difference is not included.") == 1


WRONG_TOTAL_ANSWER = "PNR001: 3500 (change fee) + 23300 (new fare) = 24000. 700 credit. Tax difference is not included."


def test_confirmed_figures_are_appended_even_when_the_model_states_a_wrong_total():
    model = FakeModel([QUOTE_PNR001, text_reply(WRONG_TOTAL_ANSWER)])
    result = run(run_agent("quote", "user-1", model, clock=fixed_clock))

    assert result.answer.startswith(WRONG_TOTAL_ANSWER)
    assert CONFIRMED_HEADER in result.answer
    assert "- PNR001 to 2026-12-12: change fee ₹3,500, fare difference -₹700, total to pay ₹3,500" in result.answer


def test_confirmed_figures_list_every_quote():
    quote_006 = tool_reply("quote_change", {"reference": "PNR006", "new_date": "2026-12-12"})
    model = FakeModel([QUOTE_PNR001, quote_006, text_reply("Both quoted.")])
    result = run(run_agent("both", "user-1", model, clock=fixed_clock))

    assert "- PNR001 to 2026-12-12" in result.answer
    assert "- PNR006 to 2026-12-12: change fee ₹500, fare difference -₹700, total to pay ₹500" in result.answer


def test_no_confirmed_figures_without_a_successful_quote():
    refused = tool_reply("quote_change", {"reference": "PNR005", "new_date": "2026-12-12"})
    model = FakeModel([refused, text_reply("That fare cannot be changed.")])
    result = run(run_agent("restricted", "user-1", model, clock=fixed_clock))

    assert result.answer == "That fare cannot be changed."
    assert CONFIRMED_HEADER not in result.answer
