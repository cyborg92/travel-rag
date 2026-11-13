"""Synthetic fare data mirroring data/policies/new-ticket-change-policy.md.

Fictional only.
Amounts are whole INR.
"""
from dataclasses import dataclass
from datetime import date, time, datetime
from pydantic import BaseModel, Field
from app.mock_backend.bookings import get_booking,Booking

# --- Fare classes and fare rule codes (policy section 11) -------------------
DEPARTURE_TIME = time(9, 0)

FARE_CLASSES = (
    "Economy Lite Restricted",
    "Economy Lite",
    "Economy Flex",
    "Business Flex",
)

FARE_CODE_BY_CLASS = {
    "Economy Lite Restricted": "FARE-K",
    "Economy Lite": "FARE-L",
    "Economy Flex": "FARE-F",
    "Business Flex": "FARE-B",
}


@dataclass(frozen=True)
class FareRule:
    fare_type: str
    changeable: bool
    condition: str


FARE_RULES = {
    "FARE-K": FareRule(
        "Restricted Economy Lite",
        False,
        "Non-changeable. No voluntary change is permitted unless an "
        "involuntary-disruption rule applies.",
    ),
    "FARE-L": FareRule(
        "Standard Economy Lite",
        True,
        "Changes follow the change fee tables. A lower new fare is not refunded.",
    ),
    "FARE-F": FareRule(
        "Economy Flex",
        True,
        "Changes follow the change fee tables. A lower new fare is issued as a "
        "travel credit valid for 12 months from the original ticket issue date.",
    ),
    "FARE-B": FareRule(
        "Business Flex",
        True,
        "Changes follow the change fee tables. A lower new fare is issued as a "
        "travel credit valid for 12 months. Same-day standby is available.",
    ),
}

# --- Domestic vs international (selects the fee table) ----------------------

DOMESTIC_AIRPORTS = frozenset({"BLR", "DEL", "BOM"})
# A route is domestic when both ends are in DOMESTIC_AIRPORTS, else international.

# --- Change fee tables (policy sections 2 and 3) ----------------------------
# Each table is a list of (hours_left_greater_than, {fare_class: fee}) bands,
# ordered from the most hours to the fewest. A band applies when the hours
# left before departure are strictly greater than its first value; the last
# band's bound is -1 so it catches everything above zero. The policy's bands
# share boundary hours (for example 24 sits in both "24 to 72" and "3 to 24");
# this data resolves that by giving the boundary hour to the later, costlier
# band. None means "not permitted".
#
# International fees in the policy are stated "up to"; these are the upper
# limits, so a quote built from them is an upper bound.
# "Economy Lite Restricted" is absent: it is non-changeable (FARE-K).

DOMESTIC_CHANGE_FEES = [
    (72, {"Economy Lite": 2000, "Economy Flex": 500, "Business Flex": 0}),
    (24, {"Economy Lite": 3000, "Economy Flex": 1000, "Business Flex": 500}),
    (3, {"Economy Lite": 4000, "Economy Flex": 2000, "Business Flex": 1000}),
    (-1, {"Economy Lite": None, "Economy Flex": None, "Business Flex": 2500}),
]

INTERNATIONAL_CHANGE_FEES = [
    (72, {"Economy Lite": 7000, "Economy Flex": 3500, "Business Flex": 1000}),
    (24, {"Economy Lite": 10000, "Economy Flex": 5000, "Business Flex": 2500}),
    (4, {"Economy Lite": 12500, "Economy Flex": 7000, "Business Flex": 4000}),
    (-1, {"Economy Lite": None, "Economy Flex": None, "Business Flex": 7000}),
]

# --- Fares (policy section 4: change fee + positive fare difference) --------
# Base fare per route and fare class. Routes are (origin, destination).

BASE_FARE_INR = {
    ("BLR", "DXB"): {"Economy Lite": 19500, "Economy Flex": 24000, "Business Flex": 52000},
    ("DEL", "BOM"): {"Economy Lite": 5200, "Economy Flex": 6500, "Business Flex": 14000},
    ("BOM", "BLR"): {"Economy Lite": 4800, "Economy Flex": 6000, "Business Flex": 13000},
    ("BLR", "DEL"): {"Economy Lite": 6000, "Economy Flex": 7500, "Business Flex": 16000},
    ("BOM", "DEL"): {"Economy Lite": 5200, "Economy Flex": 6500, "Business Flex": 14000},
}
# "Economy Lite Restricted" uses the "Economy Lite" base fare.
FARE_CLASS_PRICING_ALIAS = {"Economy Lite Restricted": "Economy Lite"}

# Date-specific adjustment added to the base fare, by ISO travel date, for any
# route and class. Dates not listed have no adjustment. Gives the change
# calculator both a higher-fare date (fare difference to pay) and a
# lower-fare date (credit or no refund).
DATE_PRICE_ADJUSTMENT_INR = {
    "2026-11-21": 800,
    "2026-11-22": -500,
    "2026-12-11": 1500,
    "2026-12-12": -700,
}

class FareRules(BaseModel):
    reference:str
    fare_code:str
    fare_type:str
    changeable:bool
    condition:str

class ChangeQuote(BaseModel):
    """Quote for moving a booking to a new date. A quote only; nothing is changed.

    When `changeable` is False, `reason` says why and the money fields stay
    None. Amounts are whole INR.
    """

    reference: str
    new_date: date
    changeable: bool
    reason: str | None = None
    change_fee: int | None = None
    old_fare: int | None = None
    new_fare: int | None = None
    fare_difference: int | None = None
    credit_issued: int = 0
    credit_valid_months: int | None = None
    total_to_pay: int | None = None
    currency: str = "INR"
    notes: list[str] = Field(default_factory=list)


def get_fare_rules(reference,user_id) -> FareRules:
    booking = get_booking(reference =reference,user_id=user_id)
    booking_class = booking.fare_class
    return rules_for_booking(reference,booking_class)

def rules_for_booking(reference:str,booking_class:str) -> FareRules:
    fare_code = FARE_CODE_BY_CLASS[booking_class]
    fare_rule = FARE_RULES[fare_code]
    return FareRules (
        reference = reference,
        fare_code = fare_code,
        fare_type = fare_rule.fare_type,
        changeable = fare_rule.changeable,
        condition = fare_rule.condition,
    )

# Classes that receive a travel credit when the new fare is lower (policy section 1).
CREDIT_CLASSES = frozenset({"Economy Flex", "Business Flex"})
CREDIT_VALID_MONTHS = 12


def quote_change(
    booking: Booking, new_date: date, now: datetime | None = None
) -> ChangeQuote:
    """Quote moving `booking` to `new_date`. A quote only; nothing is changed.

    `booking` must already be loaded through the owner check. Refusals return
    a ChangeQuote with changeable=False and a reason.
    """
    now = now or datetime.now()
    original_date = date.fromisoformat(booking.departure_date)

    def refuse(reason: str) -> ChangeQuote:
        return ChangeQuote(
            reference=booking.reference,
            new_date=new_date,
            changeable=False,
            reason=reason,
        )

    # 1-2. The booking and the fare must allow a change at all.
    if booking.status != "confirmed":
        return refuse(f"Booking is {booking.status}, so it cannot be changed")
    rules = rules_for_booking(booking.reference, booking.fare_class)
    if not rules.changeable:
        return refuse("This fare is non-changeable")

    # 3-4. The requested date must make sense.
    if new_date < now.date():
        return refuse("New date is in the past")
    if new_date == original_date:
        return refuse("New date is the same as the current departure date")

    # 5-6. The original departure must be far enough away for this fare.
    hours_left = calc_hours_left(booking.departure_date, now)
    if hours_left <= 0:
        return refuse("Departure has already passed")
    scope = route_scope(booking.origin, booking.destination)
    change_fee = fee_for(scope, booking.fare_class, hours_left)
    if change_fee is None:
        return refuse("Too close to departure for this fare")

    # Money: the fee is always payable; only a higher new fare adds to it.
    route = (booking.origin, booking.destination)
    old_fare = fare_for(*route, booking.fare_class, booking.departure_date)
    new_fare = fare_for(*route, booking.fare_class, new_date.isoformat())
    fare_difference = new_fare - old_fare

    credit_issued = 0
    credit_valid_months = None
    if fare_difference < 0 and booking.fare_class in CREDIT_CLASSES:
        credit_issued = -fare_difference
        credit_valid_months = CREDIT_VALID_MONTHS

    return ChangeQuote(
        reference=booking.reference,
        new_date=new_date,
        changeable=True,
        change_fee=change_fee,
        old_fare=old_fare,
        new_fare=new_fare,
        fare_difference=fare_difference,
        credit_issued=credit_issued,
        credit_valid_months=credit_valid_months,
        total_to_pay=change_fee + max(fare_difference, 0),
        currency = "INR",
        notes=["Tax difference is not included."],
    )


def calculate_change_options(reference: str, new_date: date, user_id: str) -> ChangeQuote:
    """The tool entry point: load the user's booking (owner check), then quote."""
    booking = get_booking(reference, user_id)
    return quote_change(booking, new_date)


def route_scope(origin: str, destination: str) -> str:
    """"domestic" only when both airports are domestic, else "international"."""
    if origin in DOMESTIC_AIRPORTS and destination in DOMESTIC_AIRPORTS:
        return "domestic"
    return "international"


def fee_for(scope: str, fare_class: str, hours_left: float) -> int | None:
    """Change fee in INR, or None when a change is not permitted this close to
    departure. A band applies when hours_left is strictly greater than its bound.
    A fare class with no fee table (the restricted fare) raises KeyError; callers
    refuse non-changeable fares before asking for a fee."""
    bands = DOMESTIC_CHANGE_FEES if scope == "domestic" else INTERNATIONAL_CHANGE_FEES
    for bound, fees in bands:
        if hours_left > bound:
            return fees[fare_class]
    return None


def fare_for(origin: str, destination: str, fare_class: str, iso_date: str) -> int:
    """Fare in INR for a route, class and travel date: base fare plus any
    date adjustment. An unknown route or class is a data bug and raises KeyError."""
    pricing_class = FARE_CLASS_PRICING_ALIAS.get(fare_class, fare_class)
    base = BASE_FARE_INR[(origin, destination)][pricing_class]
    return base + DATE_PRICE_ADJUSTMENT_INR.get(iso_date, 0)

def calc_hours_left(departure_date: str, now: datetime) -> float:
    """Hours from `now` to the booking's original scheduled departure."""
    dep_date = date.fromisoformat(departure_date)               
    departure_dt = datetime.combine(dep_date, DEPARTURE_TIME)
    hours_left = (departure_dt - now).total_seconds() / 3600
    return hours_left