import json

from app.agent.text_tool_calls import tool_calls_from_text
from app.tools.executor import execute_tool


def as_text(name, params, key="parameters") -> str:
    return json.dumps({"name": name, key: params})


def test_json_with_parameters_is_recovered_in_the_real_request_shape():
    text = as_text("quote_change", {"reference": "PNR006", "new_date": "2026-12-12"})
    assert tool_calls_from_text(text) == [
        {"function": {"name": "quote_change", "arguments": {"reference": "PNR006", "new_date": "2026-12-12"}}}
    ]


def test_json_with_arguments_key_is_also_recovered():
    text = as_text("get_booking", {"reference": "PNR001"}, key="arguments")
    assert tool_calls_from_text(text)[0]["function"]["arguments"] == {"reference": "PNR001"}


def test_empty_or_missing_text_gives_nothing():
    assert tool_calls_from_text("") == []
    assert tool_calls_from_text(None) == []


def test_plain_prose_gives_nothing():
    assert tool_calls_from_text("Now, calling the tool for PNR006.") == []


def test_unknown_tool_name_is_ignored():
    assert tool_calls_from_text(as_text("delete_everything", {"reference": "PNR001"})) == []


def test_json_that_is_not_a_tool_request_is_ignored():
    assert tool_calls_from_text(json.dumps({"reference": "PNR001", "total": 3500})) == []
    assert tool_calls_from_text("[1, 2, 3]") == []


def test_name_that_is_not_text_does_not_crash():
    assert tool_calls_from_text(json.dumps({"name": ["a"], "parameters": {}})) == []
    assert tool_calls_from_text(json.dumps({"name": 5, "parameters": {}})) == []


def test_arguments_that_are_not_an_object_are_ignored():
    assert tool_calls_from_text(as_text("get_booking", "PNR001")) == []
    assert tool_calls_from_text(as_text("get_booking", ["PNR001"])) == []
    assert tool_calls_from_text(json.dumps({"name": "get_booking"})) == []


def test_recovered_request_still_goes_through_validation_and_owner_check():
    request = tool_calls_from_text(as_text("get_booking", {"reference": "PNR001", "user_id": "user-2"}))[0]["function"]
    result = execute_tool(request["name"], request["arguments"], "user-1")
    assert result.startswith("Invalid arguments")  # a model-supplied user_id is still rejected

    request = tool_calls_from_text(as_text("get_booking", {"reference": "PNR001"}))[0]["function"]
    assert "No booking found" in execute_tool(request["name"], request["arguments"], "someone-else")
