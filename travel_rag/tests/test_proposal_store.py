from datetime import timedelta
from uuid import uuid4

import pytest

from app.proposals.models import Status
from app.proposals.store import ProposalStore
from tests.test_proposal_models import NOW, make_proposal


@pytest.fixture
def store():
    return ProposalStore(":memory:")


def test_saved_proposal_reads_back_with_every_field(store):
    proposal = make_proposal(claimed_at=NOW + timedelta(seconds=5), result={"ok": True}, status=Status.EXECUTED)
    store.save(proposal)
    assert store.get(proposal.id, "user-1") == proposal


def test_a_new_proposal_reads_back_as_pending_without_claim_or_result(store):
    proposal = make_proposal()
    store.save(proposal)
    loaded = store.get(proposal.id, "user-1")
    assert loaded.status is Status.PENDING
    assert loaded.claimed_at is None
    assert loaded.result is None


def test_missing_proposal_is_none(store):
    assert store.get(uuid4(), "user-1") is None


def test_someone_elses_proposal_is_none_exactly_like_a_missing_one(store):
    proposal = make_proposal(owner_id="user-1")
    store.save(proposal)
    assert store.get(proposal.id, "user-2") is None


def test_data_survives_reopening_a_file_database(tmp_path):
    path = str(tmp_path / "proposals.db")
    proposal = make_proposal()
    ProposalStore(path).save(proposal)
    assert ProposalStore(path).get(proposal.id, "user-1") == proposal


def test_values_are_passed_as_parameters_not_pasted_into_sql(store):
    proposal = make_proposal(owner_id="user-1'; DROP TABLE proposals; --")
    store.save(proposal)
    assert store.get(proposal.id, "user-1'; DROP TABLE proposals; --") == proposal
    assert store.get(proposal.id, "user-1") is None
