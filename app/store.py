import sqlite3
from pathlib import Path

from app.schemas import TriageResult

DEFAULT_DB = Path("triage.db")


class TriageStore:
    def __init__(self, db_path: str | Path = DEFAULT_DB):
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS results "
            "(ticket_id TEXT PRIMARY KEY, result_json TEXT NOT NULL)"
        )
        self.conn.commit()

    def get(self, ticket_id: str) -> TriageResult | None:
        row = self.conn.execute(
            "SELECT result_json FROM results WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()
        if row is None:
            return None
        return TriageResult.model_validate_json(row[0])

    def save(self, result: TriageResult) -> None:
        # INSERT OR IGNORE: the first saved result wins. A later save for the
        # same ticket does nothing, so the stored answer never changes.
        self.conn.execute(
            "INSERT OR IGNORE INTO results (ticket_id, result_json) VALUES (?, ?)",
            (result.ticket_id, result.model_dump_json()),
        )
        self.conn.commit()