from datetime import datetime, timedelta

from app.agent.state import AgentState, ToolCallRecord, call_key

START = datetime(2026, 11, 14, 10, 0, 0)


def make_state() -> AgentState:
    return AgentState(messages=[], started_at=START)


def test_call_key_ignores_argument_order():
    assert call_key("quote_change", {"reference": "PNR001", "new_date": "2026-11-21"}) == call_key(
        "quote_change", {"new_date": "2026-11-21", "reference": "PNR001"}
    )


def test_call_key_differs_by_tool_and_by_arguments():
    base = call_key("get_booking", {"reference": "PNR001"})
    assert base != call_key("get_fare_rules", {"reference": "PNR001"})
    assert base != call_key("get_booking", {"reference": "PNR002"})


def test_new_state_is_empty():
    state = make_state()
    assert state.tool_call_count == 0
    assert state.tool_calls == []


def test_count_grows_with_each_recorded_call():
    state = make_state()
    state.record_call("get_booking", {"reference": "PNR001"}, "r1")
    assert state.tool_call_count == 1
    state.record_call("get_booking", {"reference": "PNR002"}, "r2")
    assert state.tool_call_count == 2


def test_record_call_stores_a_record_with_key():
    state = make_state()
    state.record_call("get_booking", {"reference": "PNR001"}, "result")
    record = state.tool_calls[0]
    assert isinstance(record, ToolCallRecord)
    assert record.name == "get_booking"
    assert record.arguments == {"reference": "PNR001"}
    assert record.result == "result"
    assert record.key == call_key("get_booking", {"reference": "PNR001"})


def test_has_called_false_on_empty_state():
    assert make_state().has_called("get_booking", {"reference": "PNR001"}) is False


def test_has_called_finds_a_later_record_not_just_the_first():
    state = make_state()
    state.record_call("get_booking", {"reference": "PNR001"}, "r1")
    state.record_call("get_fare_rules", {"reference": "PNR001"}, "r2")
    assert state.has_called("get_fare_rules", {"reference": "PNR001"}) is True


def test_has_called_is_false_for_different_arguments():
    state = make_state()
    state.record_call("get_booking", {"reference": "PNR001"}, "r1")
    assert state.has_called("get_booking", {"reference": "PNR002"}) is False


def test_has_called_ignores_argument_order():
    state = make_state()
    state.record_call("quote_change", {"reference": "PNR001", "new_date": "2026-11-21"}, "r")
    assert state.has_called("quote_change", {"new_date": "2026-11-21", "reference": "PNR001"}) is True


def test_elapsed_uses_the_clock_passed_in():
    state = make_state()
    assert state.elapsed(START) == 0.0
    assert state.elapsed(START + timedelta(seconds=12, milliseconds=500)) == 12.5


def test_separate_states_do_not_share_the_call_log():
    first, second = make_state(), make_state()
    first.record_call("get_booking", {"reference": "PNR001"}, "r")
    assert second.tool_call_count == 0
