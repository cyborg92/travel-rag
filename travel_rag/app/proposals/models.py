import hashlib
import hmac
import json
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

class Status(Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    EXECUTED = "executed"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

ALLOWED_TRANSITIONS: dict[Status, frozenset[Status]] = {
    Status.PENDING: frozenset({
        Status.EXECUTING,
        Status.EXPIRED,
        Status.CANCELLED,
        Status.FAILED
    }),
    Status.EXECUTING: frozenset({
        Status.EXECUTING,
        Status.EXECUTED,
        Status.FAILED
    }),
    Status.EXECUTED: frozenset(),
    Status.FAILED: frozenset(),
    Status.EXPIRED: frozenset(),
    Status.CANCELLED: frozenset(),
}

class Quote(BaseModel):
    model_config = ConfigDict(frozen=True)

    change_fee: int
    fare_difference: int
    total_to_pay:int
    currency: Literal["INR"] = "INR"

class Proposal(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    owner_id: str
    action: Literal["change_booking"] = "change_booking"
    reference: str
    new_date: date
    quote: Quote
    params_hash: str
    status: Status = Status.PENDING
    created_at: datetime
    expires_at: datetime
    claimed_at: datetime | None = None
    result: dict[str, Any] | None = None
