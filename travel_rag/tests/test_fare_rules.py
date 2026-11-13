import pytest

from app.mock_backend.bookings import BookingNotFoundError, get_booking
from app.mock_backend.fares import (
    FareRules,
    get_fare_rules,
    rules_for_booking,
)


def test_flex_booking_returns_flex_rules() -> None:
    rules = get_fare_rules("PNR001", "user-1")

    assert isinstance(rules, FareRules)
    assert rules.reference == "PNR001"
    assert rules.fare_code == "FARE-F"
    assert rules.changeable is True
    assert "travel credit" in rules.condition


def test_restricted_booking_is_not_changeable() -> None:
    rules = get_fare_rules("PNR005", "user-1")

    assert rules.fare_code == "FARE-K"
    assert rules.changeable is False


def test_business_booking_returns_business_rules() -> None:
    rules = get_fare_rules("PNR003", "user-1")

    assert rules.fare_code == "FARE-B"
    assert "standby" in rules.condition.lower()


def test_other_users_booking_raises_not_found() -> None:
    with pytest.raises(BookingNotFoundError):
        get_fare_rules("PNR004", "user-1")


def test_unknown_reference_raises_not_found() -> None:
    with pytest.raises(BookingNotFoundError):
        get_fare_rules("PNR999", "user-1")


def test_rules_for_booking_matches_get_fare_rules() -> None:
    booking = get_booking("PNR006", "user-1")

    assert rules_for_booking(booking.reference, booking.fare_class) == get_fare_rules(
        "PNR006", "user-1"
    )


def test_unknown_fare_class_raises_key_error() -> None:
    with pytest.raises(KeyError):
        rules_for_booking("PNR001", "Mystery Class")
