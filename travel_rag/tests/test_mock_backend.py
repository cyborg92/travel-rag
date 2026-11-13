import pytest

from app.mock_backend.bookings import BookingNotFoundError, get_booking


def test_get_booking_returns_demo_booking() -> None:
    booking = get_booking("PNR001", "user-1")

    assert (booking.origin, booking.destination) == ("BLR", "DXB")
    assert booking.status == "confirmed"


@pytest.mark.parametrize(
    ("reference", "status"),
    [("PNR002", "cancelled"), ("PNR003", "flown")],
)
def test_edge_case_bookings_exist(reference: str, status: str) -> None:
    assert get_booking(reference, "user-1").status == status


def test_other_users_booking_raises_same_as_missing() -> None:
    with pytest.raises(BookingNotFoundError):
        get_booking("PNR004", "user-1")


def test_unknown_reference_raises() -> None:
    with pytest.raises(BookingNotFoundError):
        get_booking("PNR999", "user-1")
