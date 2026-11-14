from dataclasses import dataclass
from typing import Callable

from pydantic import BaseModel

from app.mock_backend.fares import calculate_change_options, get_fare_rules
from app.tools.schemas import GetBookingArgs, GetFareRulesArgs,QuoteChangeArgs
from app.tools.results import lookup_booking


@dataclass(frozen=True)
class ToolSpec:
    """Everything the system knows about one tool.

    `description` is written for the model: it is how the model decides when
    to call the tool. `func` always receives the caller's `user_id` in
    addition to the validated arguments; the model never supplies it.
    """

    name: str
    description: str
    args_model: type[BaseModel]
    func: Callable


_SPECS = [
    ToolSpec(
        name="get_booking",
        description=(
            "Look up one of the current user's bookings by its reference "
            "(format PNR followed by three digits, for example PNR001). Returns "
            "route, departure date, fare class and status. Only call this when "
            "the user has given a booking reference; do not guess one."
        ),
        args_model=GetBookingArgs,
        func=lookup_booking,
    ),
    ToolSpec(
        name="get_fare_rules",
        description=(
            "Answer whether one of the current user's bookings can be changed, "
            "and on what terms (change conditions, and refund or credit rules). "
            "Takes a booking reference (PNR followed by three digits, for example "
            "PNR001). Returns reference, fare_code, fare_type, changeable and "
            "condition. Does not return route or dates; use get_booking for "
            "those. Only call this when the user has given a booking reference; "
            "do not guess one."
        ),
        args_model=GetFareRulesArgs,
        func=get_fare_rules,
    ),
    ToolSpec(
        name="quote_change",
        description=(
            "Quote what it would cost to move one of the current user's bookings "
            "to a new travel date: the change fee, the fare difference between "
            "the old and new date, any travel credit, and the total to pay. If "
            "the change is not allowed, returns the reason instead. This is a "
            "quote only and changes nothing. Takes a booking reference (PNR "
            "followed by three digits, for example PNR001) and the new date as "
            "YYYY-MM-DD. Use get_fare_rules to learn whether a fare can be "
            "changed at all, and get_booking for route and dates. Only call "
            "this when the user has given both a booking reference and a new "
            "date; do not guess either. "
        ),
        args_model=QuoteChangeArgs,
        func=calculate_change_options,
    ),
]

TOOLS = {spec.name: spec for spec in _SPECS}
