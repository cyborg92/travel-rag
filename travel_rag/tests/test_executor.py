import json
from dataclasses import replace

import pytest

from app.tools import registry
from app.tools.executor import execute_tool

USER = "user-1"


def test_valid_call_returns_booking_json() -> None:
    result = json.loads(execute_tool("get_booking", {"reference": "PNR001"}, USER))

    assert result["reference"] == "PNR001"
    assert (result["origin"], result["destination"]) == ("BLR", "DXB")


def test_unknown_tool_is_rejected() -> None:
    result = execute_tool("delete_booking", {"reference": "PNR001"}, USER)

    assert "Unknown tool 'delete_booking'" in result


@pytest.mark.parametrize("reference", ["oops", "pnr001", "PNR1", "PNR0012", ""])
def test_malformed_reference_is_rejected(reference: str) -> None:
    result = execute_tool("get_booking", {"reference": reference}, USER)

    assert result.startswith("Invalid arguments for 'get_booking'")


def test_missing_argument_is_rejected() -> None:
    result = execute_tool("get_booking", {}, USER)

    assert result.startswith("Invalid arguments for 'get_booking'")


def test_extra_argument_is_rejected() -> None:
    result = execute_tool("get_booking", {"reference": "PNR001", "user_id": "x"}, USER)

    assert result.startswith("Invalid arguments for 'get_booking'")


def test_well_formed_but_unknown_reference_returns_not_found() -> None:
    result = execute_tool("get_booking", {"reference": "PNR999"}, USER)

    assert "PNR999" in result
    assert not result.startswith("Invalid arguments")


def test_tool_crash_returns_generic_message_without_internal_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def exploding_tool(reference: str, user_id: str):
        raise RuntimeError("db password=hunter2 at 10.0.0.5")

    monkeypatch.setitem(
        registry.TOOLS,
        "get_booking",
        replace(registry.TOOLS["get_booking"], func=exploding_tool),
    )

    result = execute_tool("get_booking", {"reference": "PNR001"}, USER)

    assert "hunter2" not in result
    assert "10.0.0.5" not in result
    assert "failed" in result.lower()


def test_other_users_booking_looks_like_not_found() -> None:
    result = execute_tool("get_booking", {"reference": "PNR004"}, USER)
    missing = execute_tool("get_booking", {"reference": "PNR999"}, USER)

    assert "Other Passenger" not in result
    assert "user-2" not in result
    assert result.replace("PNR004", "X") == missing.replace("PNR999", "X")


def test_owner_can_read_own_booking() -> None:
    result = json.loads(execute_tool("get_booking", {"reference": "PNR004"}, "user-2"))

    assert result["reference"] == "PNR004"
    assert result["passenger_name"] == "Other Passenger"


def test_model_cannot_supply_user_id() -> None:
    result = execute_tool(
        "get_booking", {"reference": "PNR004", "user_id": "user-2"}, USER
    )

    assert result.startswith("Invalid arguments for 'get_booking'")
    assert "Other Passenger" not in result


def test_every_registered_tool_has_a_model_facing_description() -> None:
    for name, spec in registry.TOOLS.items():
        assert spec.name == name
        assert len(spec.description) > 40


def test_fare_rules_tool_returns_rules_json() -> None:
    result = json.loads(execute_tool("get_fare_rules", {"reference": "PNR005"}, USER))

    assert result["reference"] == "PNR005"
    assert result["fare_code"] == "FARE-K"
    assert result["changeable"] is False


def test_fare_rules_tool_hides_other_users_booking() -> None:
    result = execute_tool("get_fare_rules", {"reference": "PNR004"}, USER)
    missing = execute_tool("get_fare_rules", {"reference": "PNR999"}, USER)

    assert "fare_code" not in result
    assert "user-2" not in result
    assert result.replace("PNR004", "X") == missing.replace("PNR999", "X")


@pytest.mark.parametrize(
    "arguments",
    [
        {"reference": "oops"},
        {},
        {"reference": "PNR001", "user_id": "user-2"},
    ],
)
def test_fare_rules_tool_rejects_bad_arguments(arguments: dict) -> None:
    result = execute_tool("get_fare_rules", arguments, USER)

    assert result.startswith("Invalid arguments for 'get_fare_rules'")


def test_fare_rules_tool_crash_returns_generic_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def exploding_tool(reference: str, user_id: str):
        raise KeyError("Mystery Class")

    monkeypatch.setitem(
        registry.TOOLS,
        "get_fare_rules",
        replace(registry.TOOLS["get_fare_rules"], func=exploding_tool),
    )

    result = execute_tool("get_fare_rules", {"reference": "PNR001"}, USER)

    assert "Mystery Class" not in result
    assert "failed" in result.lower()


def test_quote_tool_returns_a_quote_json() -> None:
    result = json.loads(
        execute_tool(
            "quote_change", {"reference": "PNR006", "new_date": "2099-12-11"}, USER
        )
    )

    assert result["reference"] == "PNR006"
    assert "changeable" in result


def test_quote_tool_refuses_a_non_changeable_fare() -> None:
    result = json.loads(
        execute_tool(
            "quote_change", {"reference": "PNR005", "new_date": "2026-12-05"}, USER
        )
    )

    assert result["changeable"] is False
    assert "non-changeable" in result["reason"]


def test_quote_tool_hides_other_users_booking() -> None:
    result = execute_tool(
        "quote_change", {"reference": "PNR004", "new_date": "2026-12-06"}, USER
    )
    missing = execute_tool(
        "quote_change", {"reference": "PNR999", "new_date": "2026-12-06"}, USER
    )

    assert "total_to_pay" not in result
    assert "user-2" not in result
    assert result.replace("PNR004", "X") == missing.replace("PNR999", "X")


@pytest.mark.parametrize(
    "arguments",
    [
        {"reference": "PNR001", "new_date": "tomorrow"},
        {"reference": "PNR001", "new_date": "2026-13-45"},
        {"reference": "PNR001"},
        {"new_date": "2026-11-21"},
        {"reference": "PNR001", "new_date": "2026-11-21", "now": "2026-11-20T08:00"},
        {"reference": "PNR001", "new_date": "2026-11-21", "user_id": "user-2"},
    ],
)
def test_quote_tool_rejects_bad_arguments(arguments: dict) -> None:
    result = execute_tool("quote_change", arguments, USER)

    assert result.startswith("Invalid arguments for 'quote_change'")
