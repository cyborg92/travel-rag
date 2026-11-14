import itertools

import pytest

from app.proposals.models import ALLOWED_TRANSITIONS, Status
from app.proposals.transitions import InvalidTransitionError, transition
from tests.test_proposal_models import make_proposal

LEGAL = [(a, b) for a, targets in ALLOWED_TRANSITIONS.items() for b in targets]
ILLEGAL = [
    (a, b) for a, b in itertools.product(Status, Status) if b not in ALLOWED_TRANSITIONS[a]
]


@pytest.mark.parametrize("start,end", LEGAL, ids=lambda s: s.value)
def test_every_legal_move_is_applied(start, end):
    proposal = make_proposal(status=start)
    transition(proposal, end)
    assert proposal.status is end


@pytest.mark.parametrize("start,end", ILLEGAL, ids=lambda s: s.value)
def test_every_illegal_move_raises_and_changes_nothing(start, end):
    proposal = make_proposal(status=start)
    with pytest.raises(InvalidTransitionError):
        transition(proposal, end)
    assert proposal.status is start


def test_the_error_names_both_states():
    proposal = make_proposal(status=Status.EXECUTED)
    with pytest.raises(InvalidTransitionError) as error:
        transition(proposal, Status.PENDING)
    assert "executed" in str(error.value).lower()
    assert "pending" in str(error.value).lower()


def test_a_normal_lifecycle_walks_through():
    proposal = make_proposal()
    transition(proposal, Status.EXECUTING)
    transition(proposal, Status.EXECUTED)
    assert proposal.status is Status.EXECUTED


def test_an_executed_proposal_cannot_be_executed_again():
    proposal = make_proposal()
    transition(proposal, Status.EXECUTING)
    transition(proposal, Status.EXECUTED)
    with pytest.raises(InvalidTransitionError):
        transition(proposal, Status.EXECUTING)


def test_a_claimed_proposal_can_be_reclaimed():
    proposal = make_proposal()
    transition(proposal, Status.EXECUTING)
    transition(proposal, Status.EXECUTING)
    assert proposal.status is Status.EXECUTING


def test_claimed_at_is_empty_until_claimed():
    assert make_proposal().claimed_at is None
