"""Argument models for tools: the shape of what the model is allowed to send.

These are the trust boundary's input contract. They never contain `user_id`
or any other identity or clock value; application code supplies those.
"""
from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class GetBookingArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference: str = Field(pattern=r"^PNR\d{3}$")

class GetFareRulesArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reference: str = Field(pattern=r"^PNR\d{3}$")

class QuoteChangeArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reference: str = Field(pattern=r"^PNR\d{3}$")
    new_date:date