"""Demo routes: deterministic code paths exposed for showcasing, no model needed.

Only mounted when TRAVEL_RAG_ENABLE_DEMO_ROUTES is true (see app/main.py).
There is no authentication on these routes; share the URL only with intended viewers.

The caller is always the fixed synthetic user below. It is never read from the
request, which mirrors the tool trust boundary: identity comes from application
code, not from the client or the model.

Each route carries named request examples (the Swagger "Examples" dropdown). The
matching response examples are produced by running the real code when this module
is imported, so the documentation cannot drift from the behaviour.
"""
from datetime import date, datetime

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.mock_backend.bookings import BookingNotFoundError, get_booking
from app.mock_backend.fares import ChangeQuote, quote_change
from app.tools.executor import execute_tool

DEMO_USER_ID = "user-1"

router = APIRouter(prefix="/demo", tags=["demo"])


# --- POST /demo/tools/execute ------------------------------------------------


class ToolExecuteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Tool name, exactly as a model would send it.")
    arguments: dict = Field(
        description="Tool arguments, exactly as a model would send them. Validated "
        "against the tool's schema, which forbids unknown keys."
    )


class ToolExecuteResponse(BaseModel):
    user_id: str = Field(description="The caller the server used. Fixed; never taken from the request.")
    observation: str = Field(
        description="The string the model would receive back: a JSON result, or an error message it can act on."
    )


EXECUTE_EXAMPLES = {
    "own_booking": {
        "summary": "1. Your own booking",
        "description": "PNR001 belongs to the demo user, so the booking comes back. "
        "Note the result is a trimmed view: it carries no owner id.",
        "value": {"name": "get_booking", "arguments": {"reference": "PNR001"}},
    },
    "not_yours": {
        "summary": "2. Someone else's booking (PNR004)",
        "description": "PNR004 exists but belongs to another user. The data layer refuses it "
        "with 'No booking found'. Compare with example 3.",
        "value": {"name": "get_booking", "arguments": {"reference": "PNR004"}},
    },
    "missing": {
        "summary": "3. A booking that does not exist (PNR999)",
        "description": "Same message as example 2, differing only in the reference. Missing and "
        "'not yours' look identical, so the model cannot be used to probe which references exist.",
        "value": {"name": "get_booking", "arguments": {"reference": "PNR999"}},
    },
    "identity_injection": {
        "summary": "4. Model tries to supply an identity",
        "description": "The model adds user_id: user-2 to read PNR004. The argument schema forbids "
        "extra keys, so the request is rejected before any data is touched. Identity comes only from "
        "application code.",
        "value": {"name": "get_booking", "arguments": {"reference": "PNR004", "user_id": "user-2"}},
    },
    "unknown_tool": {
        "summary": "5. A tool that does not exist",
        "description": "The model invents cancel_booking. Only registered tools run, and none can "
        "change a booking. The model gets an error it can recover from.",
        "value": {"name": "cancel_booking", "arguments": {"reference": "PNR001"}},
    },
    "bad_reference": {
        "summary": "6. Malformed reference",
        "description": "'my booking' does not match the format PNR followed by three digits. "
        "The validation error is returned as an observation so the model can ask the user.",
        "value": {"name": "get_booking", "arguments": {"reference": "my booking"}},
    },
    "placeholder_date": {
        "summary": "7. Placeholder date (seen on a live model)",
        "description": "A local model once sent the literal text YYYY-MM-DD as the date. "
        "Validation rejects it instead of guessing, and the model then asked the user.",
        "value": {"name": "quote_change", "arguments": {"reference": "PNR001", "new_date": "YYYY-MM-DD"}},
    },
    "fare_rules_restricted": {
        "summary": "8. Fare rules for a restricted fare",
        "description": "PNR005 is on a restricted fare (code FARE-K), so changeable is false. "
        "This is the answer behind 'can I change PNR005?', with no date invented.",
        "value": {"name": "get_fare_rules", "arguments": {"reference": "PNR005"}},
    },
}


def _run_execute(value: dict) -> dict:
    request = ToolExecuteRequest.model_validate(value)
    return ToolExecuteResponse(
        user_id=DEMO_USER_ID,
        observation=execute_tool(request.name, request.arguments, DEMO_USER_ID),
    ).model_dump()


EXECUTE_RESPONSE_EXAMPLES = {
    key: {"summary": example["summary"], "value": _run_execute(example["value"])}
    for key, example in EXECUTE_EXAMPLES.items()
}


@router.post(
    "/tools/execute",
    summary="Run a tool request through the trust boundary",
    response_model=ToolExecuteResponse,
    responses={200: {"content": {"application/json": {"examples": EXECUTE_RESPONSE_EXAMPLES}}}},
)
def demo_execute_tool(
    request: ToolExecuteRequest = Body(openapi_examples=EXECUTE_EXAMPLES),
) -> ToolExecuteResponse:
    """Send a tool request exactly as a model would, and see what the model would observe.

    **How to use:** open *Try it out*, pick an example from the **Examples** dropdown, press
    *Execute*, and compare with the response examples listed under *Responses*.

    **What it demonstrates** (the model only *requests*; application code does the rest):

    1. Unknown tools are refused.
    2. Arguments are validated against a strict schema (unknown keys are rejected).
    3. The caller is fixed to the demo user `user-1`; the request cannot choose it.
    4. Authorization happens in the data layer: a missing booking and another user's
       booking return the same message.
    5. Every failure comes back as a string observation, not an exception.

    No model is involved, so every call is deterministic. Tools available: `get_booking`,
    `get_fare_rules`, `quote_change` (quote only; nothing can change a booking). For a quote with a
    fixed clock, use `POST /demo/tools/quote`.
    """
    observation = execute_tool(request.name, request.arguments, DEMO_USER_ID)
    return ToolExecuteResponse(user_id=DEMO_USER_ID, observation=observation)


# --- POST /demo/tools/quote --------------------------------------------------


class QuoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference: str = Field(pattern=r"^PNR\d{3}$", description="Booking reference: PNR plus three digits.")
    new_date: date = Field(description="The date to move the booking to.")
    now: datetime | None = Field(
        default=None,
        description="Pretend the current time is this. Fee bands depend on hours left before "
        "departure (departures are at 09:00), so a fixed value makes the quote repeatable. "
        "Omit it to use the server clock.",
    )


QUOTE_EXAMPLES = {
    "costlier_date": {
        "summary": "1. Costlier date: fee plus fare difference",
        "description": "PNR001 (international, Economy Flex) moves to a date that costs 800 more. "
        "Total to pay is the change fee plus the fare difference.",
        "value": {"reference": "PNR001", "new_date": "2026-11-21", "now": "2026-11-12T10:00:00"},
    },
    "cheaper_date_credit": {
        "summary": "2. Cheaper date: credit, fee still charged",
        "description": "The new date is 500 cheaper. Flex fares receive that difference as travel "
        "credit, but the change fee is still payable and nothing is refunded in cash.",
        "value": {"reference": "PNR001", "new_date": "2026-11-22", "now": "2026-11-12T10:00:00"},
    },
    "domestic_credit": {
        "summary": "3. Domestic Flex fare with credit",
        "description": "PNR006 is a domestic Economy Flex booking. A 700 cheaper date gives 700 credit "
        "and a lower fee than the international example.",
        "value": {"reference": "PNR006", "new_date": "2026-12-12", "now": "2026-11-12T10:00:00"},
    },
    "boundary_exactly_72h": {
        "summary": "4. Boundary: exactly 72 hours before departure",
        "description": "Departure is 2026-12-10 09:00 and now is exactly 72 hours earlier. A band "
        "applies only when hours left is strictly greater than its bound, so this falls in the later, "
        "dearer band (fee 1000). Compare with example 5.",
        "value": {"reference": "PNR006", "new_date": "2026-12-11", "now": "2026-12-07T09:00:00"},
    },
    "boundary_73h": {
        "summary": "5. Boundary: 73 hours before departure",
        "description": "One hour earlier than example 4. Now more than 72 hours remain, so the lower "
        "band applies (fee 500).",
        "value": {"reference": "PNR006", "new_date": "2026-12-11", "now": "2026-12-07T08:00:00"},
    },
    "too_close": {
        "summary": "6. Refusal: too close to departure",
        "description": "Under three hours before departure this fare cannot be changed. The quote "
        "comes back with changeable false and a reason; the money fields stay empty.",
        "value": {"reference": "PNR006", "new_date": "2026-12-11", "now": "2026-12-10T07:00:00"},
    },
    "non_changeable_fare": {
        "summary": "7. Refusal: non-changeable fare",
        "description": "PNR005 is on a restricted fare (FARE-K), so no date is acceptable.",
        "value": {"reference": "PNR005", "new_date": "2026-12-05", "now": "2026-11-12T10:00:00"},
    },
    "cancelled_booking": {
        "summary": "8. Refusal: cancelled booking",
        "description": "PNR002 is already cancelled, so it cannot be changed.",
        "value": {"reference": "PNR002", "new_date": "2026-11-26", "now": "2026-11-12T10:00:00"},
    },
    "not_yours": {
        "summary": "9. Someone else's booking",
        "description": "PNR004 belongs to another user, so the response is 404 'No booking found', "
        "the same as for a booking that does not exist.",
        "value": {"reference": "PNR004", "new_date": "2026-12-20", "now": "2026-11-12T10:00:00"},
    },
}


def _quote(request: QuoteRequest) -> ChangeQuote:
    try:
        booking = get_booking(request.reference, DEMO_USER_ID)
    except BookingNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return quote_change(booking, request.new_date, request.now)


def _run_quote(value: dict) -> dict | None:
    try:
        return _quote(QuoteRequest.model_validate(value)).model_dump(mode="json")
    except HTTPException:
        return None


QUOTE_RESPONSE_EXAMPLES = {
    key: {"summary": example["summary"], "value": quote}
    for key, example in QUOTE_EXAMPLES.items()
    if (quote := _run_quote(example["value"])) is not None
}


@router.post(
    "/tools/quote",
    summary="Quote moving a booking to a new date",
    response_model=ChangeQuote,
    responses={
        200: {"content": {"application/json": {"examples": QUOTE_RESPONSE_EXAMPLES}}},
        404: {
            "description": "No such booking for the demo user (missing and not-yours are identical).",
            "content": {"application/json": {"example": {"detail": "No booking found for PNR004"}}},
        },
    },
)
def demo_quote_change(request: QuoteRequest = Body(openapi_examples=QUOTE_EXAMPLES)) -> ChangeQuote:
    """Quote a date change for one of the demo user's bookings. A quote only; nothing changes.

    **How to use:** open *Try it out*, pick an example from the **Examples** dropdown, press
    *Execute*. Each example sets `now` explicitly, so the result is the same every time.

    **What it demonstrates:** the business rules live in a pure function that takes the clock as an
    input, so they are testable and repeatable without waiting for real time to pass:

    - Fee bands by hours before departure, including the exact 72-hour boundary (examples 4 and 5).
    - Travel credit only for Flex and Business fares; the change fee is always charged.
    - Refusals returned as data (`changeable: false` with a `reason`), not as errors (examples 6 to 8).
    - The same owner check as the tools: another user's booking is a 404 identical to a missing one.

    All amounts are whole INR. Departures are at 09:00. Fares are synthetic.
    """
    return _quote(request)
