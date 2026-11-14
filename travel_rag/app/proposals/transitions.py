from app.proposals.models import Proposal, Status, ALLOWED_TRANSITIONS


class InvalidTransitionError(Exception):
    pass


def transition(proposal: Proposal, new_status: Status) -> None:
    if new_status not in ALLOWED_TRANSITIONS[proposal.status]:
        raise InvalidTransitionError(
            f"Invalid transition from {proposal.status} to {new_status}"
        )
    proposal.status = new_status