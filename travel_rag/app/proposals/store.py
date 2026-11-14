import json
import sqlite3
from uuid import UUID

from app.proposals.models import Proposal

# Insert only. A state change must never be a blind overwrite from a possibly
# stale copy; it goes through a method that carries its own condition.
SAVE_SQL = """
    INSERT INTO proposals (id, owner_id, status, claimed_at, expires_at, result_json, data)
    VALUES (?, ?, ?, ?, ?, ?, ?)
"""

GET_SQL = """
    SELECT id, owner_id, status, claimed_at, expires_at, result_json, data
    FROM proposals
    WHERE id = ? AND owner_id = ?
"""

class ProposalStore:
    def __init__(self, db_path: str) -> None:
        self._conn = sqlite3.connect(db_path)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS proposals (
                id           TEXT PRIMARY KEY,
                owner_id     TEXT NOT NULL,
                status       TEXT NOT NULL,
                claimed_at   TEXT,
                expires_at   TEXT NOT NULL,
                result_json  TEXT,
                data         TEXT NOT NULL    -- fixed fields as JSON
            )
        """)
        self._conn.commit()

    def save(self, proposal: Proposal) -> None:
        fixed = {
            "action": proposal.action,
            "reference": proposal.reference,
            "new_date": proposal.new_date.isoformat(),
            "quote": proposal.quote.model_dump(),
            "params_hash": proposal.params_hash,
            "created_at": proposal.created_at.isoformat(),
        }   

        params = (
            str(proposal.id),
            proposal.owner_id,
            proposal.status.value,
            proposal.claimed_at.isoformat() if proposal.claimed_at else None,
            proposal.expires_at.isoformat(),
            json.dumps(proposal.result) if proposal.result is not None else None,
            json.dumps(fixed, sort_keys=True),
        )

        with self._conn:
            self._conn.execute(SAVE_SQL, params)

    def get(self, proposal_id: UUID, owner_id: str) -> Proposal | None:
        row = self._conn.execute(GET_SQL, (str(proposal_id), owner_id)).fetchone()
        if row is None:
            return None

        (id_, row_owner, status, claimed_at, expires_at, result_json, data) = row
        fixed = json.loads(data)

        return Proposal(
            id=id_,
            owner_id=row_owner,
            status=status,
            claimed_at=claimed_at,
            expires_at=expires_at,
            result=json.loads(result_json) if result_json else None,
            **fixed,
        )
