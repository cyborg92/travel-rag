import json

import pytest

from app.mock_backend.bookings import Booking, BookingNotFoundError
from app.tools.executor import execute_tool
from app.tools.results import BookingView, lookup_booking


def test_tool_result_does_not_contain_the_owner():
    result = json.loads(execute_tool("get_booking", {"reference": "PNR001"}, "user-1"))
    assert "owner_id" not in result
    assert "user-1" not in json.dumps(result)


def test_tool_result_keeps_what_the_model_needs():
    result = json.loads(execute_tool("get_booking", {"reference": "PNR001"}, "user-1"))
    assert result == {
        "reference": "PNR001",
        "passenger_name": "Demo Passenger",
        "origin": "BLR",
        "destination": "DXB",
        "departure_date": "2026-11-20",
        "fare_class": "Economy Flex",
        "status": "confirmed",
    }


def test_someone_elses_booking_and_a_missing_one_still_look_identical():
    other = execute_tool("get_booking", {"reference": "PNR004"}, "user-1")
    missing = execute_tool("get_booking", {"reference": "PNR999"}, "user-1")
    assert other.replace("PNR004", "X") == missing.replace("PNR999", "X")


def test_lookup_still_enforces_the_owner_check():
    with pytest.raises(BookingNotFoundError):
        lookup_booking("PNR004", "user-1")


def test_view_only_exposes_fields_it_declares(monkeypatch):
    """A field added to Booking later must not reach the model unless the view lists it."""

    class BookingWithEmail(Booking):
        email: str = "someone@example.com"

    booking = BookingWithEmail(
        reference="PNR001", owner_id="user-1", passenger_name="Demo Passenger",
        origin="BLR", destination="DXB", departure_date="2026-11-20",
        fare_class="Economy Flex", status="confirmed",
    )
    monkeypatch.setattr("app.tools.results.get_booking", lambda reference, user_id: booking)

    view = lookup_booking("PNR001", "user-1")
    assert isinstance(view, BookingView)
    dumped = view.model_dump()
    assert "email" not in dumped
    assert "owner_id" not in dumped


def test_quote_and_fare_rule_tools_still_work_with_the_full_booking():
    quote = json.loads(execute_tool("quote_change", {"reference": "PNR001", "new_date": "2026-12-12"}, "user-1"))
    assert quote["changeable"] is True
    rules = json.loads(execute_tool("get_fare_rules", {"reference": "PNR001"}, "user-1"))
    assert rules["reference"] == "PNR001"
    assert rules["fare_code"] == "FARE-F"
    assert "owner_id" not in rules
