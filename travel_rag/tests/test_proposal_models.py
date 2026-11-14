from datetime import date, datetime, timedelta
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.proposals.models import ALLOWED_TRANSITIONS, Proposal, Quote, Status

NOW = datetime(2026, 11, 14, 10, 0, 0)
TERMINAL = {Status.EXECUTED, Status.FAILED, Status.EXPIRED, Status.CANCELLED}


def make_quote(**overrides) -> Quote:
    values = {"change_fee": 3500, "fare_difference": -700, "total_to_pay": 3500}
    return Quote(**{**values, **overrides})


def make_proposal(**overrides) -> Proposal:
    values = {
        "owner_id": "user-1",
        "reference": "PNR001",
        "new_date": "2026-12-12",
        "quote": make_quote(),
        "params_hash": "abc",
        "created_at": NOW,
        "expires_at": NOW + timedelta(minutes=10),
    }
    return Proposal(**{**values, **overrides})


# ---- the transition table

def test_every_status_has_an_entry_in_the_table():
    assert set(ALLOWED_TRANSITIONS) == set(Status)


def test_every_target_is_a_real_status():
    for targets in ALLOWED_TRANSITIONS.values():
        assert targets <= set(Status)


@pytest.mark.parametrize("status", sorted(TERMINAL, key=lambda s: s.value))
def test_terminal_states_have_no_way_out(status):
    assert ALLOWED_TRANSITIONS[status] == frozenset()


def test_pending_cannot_skip_the_claim():
    assert Status.EXECUTED not in ALLOWED_TRANSITIONS[Status.PENDING]
    assert Status.EXECUTING in ALLOWED_TRANSITIONS[Status.PENDING]


def test_pending_can_expire_cancel_or_be_rejected():
    assert {Status.EXPIRED, Status.CANCELLED, Status.FAILED} <= ALLOWED_TRANSITIONS[Status.PENDING]


def test_executing_can_finish_fail_or_be_reclaimed():
    assert ALLOWED_TRANSITIONS[Status.EXECUTING] == {Status.EXECUTING, Status.EXECUTED, Status.FAILED}


def test_nothing_moves_back_to_pending():
    assert all(Status.PENDING not in targets for targets in ALLOWED_TRANSITIONS.values())


def test_only_pending_and_executing_can_move_at_all():
    movable = {status for status, targets in ALLOWED_TRANSITIONS.items() if targets}
    assert movable == {Status.PENDING, Status.EXECUTING}


# ---- the models

def test_new_proposal_starts_pending_with_a_unique_id():
    first, second = make_proposal(), make_proposal()
    assert first.status is Status.PENDING
    assert isinstance(first.id, UUID)
    assert first.id != second.id
    assert first.result is None


def test_new_date_is_parsed_from_an_iso_string():
    assert make_proposal(new_date="2026-12-12").new_date == date(2026, 12, 12)
    with pytest.raises(ValidationError):
        make_proposal(new_date="not a date")


def test_quote_is_immutable():
    quote = make_quote()
    with pytest.raises(ValidationError):
        quote.total_to_pay = 1


def test_quote_currency_is_inr_only():
    assert make_quote().currency == "INR"
    with pytest.raises(ValidationError):
        make_quote(currency="USD")


def test_only_the_change_booking_action_exists():
    with pytest.raises(ValidationError):
        make_proposal(action="cancel_booking")
