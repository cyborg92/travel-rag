"""Synthetic booking data standing in for a real booking system. Fictional only."""
from pydantic import BaseModel


class Booking(BaseModel):
    reference: str
    owner_id: str
    passenger_name: str
    origin: str
    destination: str
    departure_date: str  # ISO date
    fare_class: str
    status: str  # "confirmed" | "cancelled" | "flown"


class BookingNotFoundError(Exception):
    pass


_BOOKINGS = {
    booking.reference: booking
    for booking in [
        Booking(
            reference="PNR001", owner_id="user-1", passenger_name="Demo Passenger",
            origin="BLR", destination="DXB", departure_date="2026-11-20",
            fare_class="Economy Flex", status="confirmed",
        ),
        Booking(
            reference="PNR002", owner_id="user-1", passenger_name="Demo Passenger",
            origin="DEL", destination="BOM", departure_date="2026-11-25",
            fare_class="Economy Lite", status="cancelled",
        ),
        Booking(
            reference="PNR003", owner_id="user-1", passenger_name="Demo Passenger",
            origin="BOM", destination="BLR", departure_date="2026-10-01",
            fare_class="Business Flex", status="flown",
        ),
        Booking(
            reference="PNR004", owner_id="user-2", passenger_name="Other Passenger",
            origin="BLR", destination="DEL", departure_date="2026-12-05",
            fare_class="Economy Lite", status="confirmed",
        ),
        Booking(
            reference="PNR005", owner_id="user-1", passenger_name="Demo Passenger",
            origin="DEL", destination="BOM", departure_date="2026-12-03",
            fare_class="Economy Lite Restricted", status="confirmed",
        ),
        Booking(
            reference="PNR006", owner_id="user-1", passenger_name="Demo Passenger",
            origin="BOM", destination="DEL", departure_date="2026-12-10",
            fare_class="Economy Flex", status="confirmed",
        ),
    ]
}


def get_booking(reference: str, user_id: str) -> Booking:
    """Return the booking for a reference or raise BookingNotFoundError."""
    booking = _BOOKINGS.get(reference)
    if booking is None or booking.owner_id != user_id:
        raise BookingNotFoundError(f"No booking found for {reference}")
    return booking