"""Demo routes: deterministic code paths exposed for showcasing, no model needed.

Only mounted when TRAVEL_RAG_ENABLE_DEMO_ROUTES is true (see app/main.py).
There is no authentication on these routes; share the URL only with intended viewers.

The caller is always the fixed synthetic user below. It is never read from the
request, which mirrors the tool trust boundary: identity comes from application
code, not from the client or the model.
"""
from datetime import date, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.mock_backend.bookings import BookingNotFoundError, get_booking
from app.mock_backend.fares import ChangeQuote, quote_change
from app.tools.executor import execute_tool

DEMO_USER_ID = "user-1"

router = APIRouter(prefix="/demo", tags=["demo"])


class ToolExecuteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(examples=["get_booking"])
    arguments: dict = Field(examples=[{"reference": "PNR004"}])


class ToolExecuteResponse(BaseModel):
    user_id: str
    observation: str


@router.post("/tools/execute", response_model=ToolExecuteResponse)
def demo_execute_tool(request: ToolExecuteRequest) -> ToolExecuteResponse:
    """Send a tool request exactly as a model would, and see what it would observe.

    The caller is fixed to the demo user (user-1). Try: an unknown tool name; a
    bad reference; an extra `user_id` argument (rejected); PNR004 (another
    user's booking) versus PNR999 (missing), which return the same message.
    """
    observation = execute_tool(request.name, request.arguments, DEMO_USER_ID)
    return ToolExecuteResponse(user_id=DEMO_USER_ID, observation=observation)


class QuoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference: str = Field(pattern=r"^PNR\d{3}$", examples=["PNR001"])
    new_date: date
    now: datetime | None = Field(
        default=None,
        description="Pretend the current time is this, to show the 72-hour fee bands.",
        examples=["2026-11-12T10:00:00"],
    )


@router.post("/tools/quote", response_model=ChangeQuote)
def demo_quote_change(request: QuoteRequest) -> ChangeQuote:
    """Quote a date change with an optional fixed `now`. A quote only; nothing changes."""
    try:
        booking = get_booking(request.reference, DEMO_USER_ID)
    except BookingNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return quote_change(booking, request.new_date, request.now)
