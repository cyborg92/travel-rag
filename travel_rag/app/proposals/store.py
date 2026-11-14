import sqlite3
import json
from app.proposals.models import Proposal 
SAVE_SQL = """
    INSERT INTO proposals (id, owner_id, status, claimed_at, expires_at, result_json, data)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        status      = excluded.status,
        claimed_at  = excluded.claimed_at,
        result_json = excluded.result_json
"""

GET_SQL = """
    SELECT id, owner_id, status, claimed_at, expires_at, result_json, data
    FROM proposals
    WHERE id = ?
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

    def save(self, proposal) ->None:
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

    def get(self, proposal_id, owner_id) -> Proposal | None:
        row = self._conn.execute(GET_SQL, (str(proposal_id),)).fetchone()
        if row is None:
            return None

        (id_, owner_id, status, claimed_at, expires_at, result_json, data) = row
        fixed = json.loads(data)

        return Proposal(
            id=id_,
            owner_id=owner_id,
            status=status,
            claimed_at=claimed_at,
            expires_at=expires_at,
            result=json.loads(result_json) if result_json else None,
            **fixed,
        )
