from pydantic import BaseModel
from app.mock_backend.bookings import get_booking

class BookingView(BaseModel):
    reference: str
    passenger_name: str
    origin: str
    destination: str
    departure_date: str  # ISO date
    fare_class: str
    status: str  # "confirmed" | "cancelled" | "flown"

def lookup_booking(reference: str, user_id: str) -> BookingView:
    booking = get_booking(reference, user_id)
    return BookingView.model_validate(booking.model_dump())
