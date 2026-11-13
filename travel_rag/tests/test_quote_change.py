from datetime import date, datetime

import pytest

from app.mock_backend.bookings import Booking, get_booking
from app.mock_backend.fares import quote_change

NOW = datetime(2026, 11, 12, 10, 0)


def quote(reference: str, new_date: str, now: datetime = NOW, user: str = "user-1"):
    return quote_change(get_booking(reference, user), date.fromisoformat(new_date), now)


def test_international_costlier_date() -> None:
    q = quote("PNR001", "2026-11-21")

    assert q.changeable is True
    assert (q.change_fee, q.old_fare, q.new_fare) == (3500, 24000, 24800)
    assert (q.fare_difference, q.credit_issued, q.total_to_pay) == (800, 0, 4300)


def test_international_cheaper_date_gives_credit_and_still_charges_fee() -> None:
    q = quote("PNR001", "2026-11-22")

    assert q.fare_difference == -500
    assert (q.credit_issued, q.credit_valid_months) == (500, 12)
    assert q.total_to_pay == 3500


def test_domestic_costlier_date() -> None:
    q = quote("PNR006", "2026-12-11")

    assert (q.change_fee, q.fare_difference, q.total_to_pay) == (500, 1500, 2000)


def test_domestic_cheaper_date() -> None:
    q = quote("PNR006", "2026-12-12")

    assert (q.fare_difference, q.credit_issued, q.total_to_pay) == (-700, 700, 500)


def test_middle_fee_band() -> None:
    q = quote("PNR006", "2026-12-11", now=datetime(2026, 12, 8, 9, 0))  # 48 h

    assert q.change_fee == 1000


def test_exactly_72_hours_uses_the_later_band() -> None:
    q = quote("PNR006", "2026-12-11", now=datetime(2026, 12, 7, 9, 0))  # 72 h

    assert q.change_fee == 1000


def test_lite_fare_gets_no_credit() -> None:
    lite = Booking(
        reference="PNR900", owner_id="user-1", passenger_name="Test",
        origin="DEL", destination="BOM", departure_date="2026-12-10",
        fare_class="Economy Lite", status="confirmed",
    )

    q = quote_change(lite, date(2026, 12, 12), NOW)  # DEL-BOM is 700 cheaper that day

    assert q.fare_difference == -700
    assert (q.credit_issued, q.credit_valid_months) == (0, None)
    assert q.total_to_pay == 2000


@pytest.mark.parametrize(
    ("reference", "new_date", "now", "reason"),
    [
        ("PNR002", "2026-11-26", NOW, "cancelled"),
        ("PNR003", "2026-11-26", NOW, "flown"),
        ("PNR005", "2026-12-05", NOW, "non-changeable"),
        ("PNR001", "2026-11-01", NOW, "in the past"),
        ("PNR001", "2026-11-20", NOW, "same as the current"),
        ("PNR006", "2026-12-11", datetime(2026, 12, 10, 7, 0), "Too close"),
        ("PNR006", "2026-12-11", datetime(2026, 12, 10, 10, 0), "already passed"),
    ],
)
def test_refusals(reference: str, new_date: str, now: datetime, reason: str) -> None:
    q = quote(reference, new_date, now)

    assert q.changeable is False
    assert reason in q.reason
    assert q.change_fee is None and q.total_to_pay is None


def test_quote_without_now_uses_the_clock() -> None:
    q = quote_change(get_booking("PNR006", "user-1"), date(2026, 12, 11))

    assert isinstance(q.changeable, bool)
