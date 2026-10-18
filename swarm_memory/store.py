import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        with self._connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS candidates (
                    id TEXT PRIMARY KEY,
                    fact_key TEXT,
                    value TEXT,
                    agent_id TEXT,
                    evidence_json TEXT,
                    write_class TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS decision_instances (
                    id TEXT PRIMARY KEY,
                    fact_key TEXT,
                    status TEXT,
                    final_class TEXT,
                    bar REAL,
                    confidence REAL,
                    value TEXT,
                    dissent TEXT,
                    evidence_json TEXT,
                    agent_id TEXT,
                    supersedes TEXT,
                    index_dirty INTEGER,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS fact_bindings (
                    fact_key TEXT PRIMARY KEY,
                    decision_id TEXT,
                    value TEXT,
                    risk_floor TEXT,
                    updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS recall_log (
                    id TEXT PRIMARY KEY,
                    query TEXT,
                    returned_ids_json TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS memory_utility (
                    decision_id TEXT PRIMARY KEY,
                    successes REAL NOT NULL,
                    trials REAL NOT NULL
                );
                """
            )

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.path)
        try:
            conn.row_factory = sqlite3.Row
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def save_candidate(self, candidate_id: str, fact_key: str | None, value: str, agent_id: str, evidence_ids: list[str], write_class: str) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO candidates (id, fact_key, value, agent_id, evidence_json, write_class, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (candidate_id, fact_key, value, agent_id, json.dumps(evidence_ids), write_class, _utc_now()),
            )

    def experience_agents(self, candidate_ids) -> list[str]:
        """Agent id of each id that names a stored experience. Other ids are skipped."""
        ids = list(dict.fromkeys(candidate_ids))
        if not ids:
            return []
        marks = ",".join("?" for _ in ids)
        with self._connection() as conn:
            rows = conn.execute(
                f"SELECT agent_id FROM candidates WHERE write_class = 'experience' AND id IN ({marks})",
                ids,
            ).fetchall()
        return [row["agent_id"] for row in rows]

    def save_instance(
        self,
        instance_id: str,
        fact_key: str | None,
        status: str,
        final_class: str | None,
        bar: float | None,
        confidence: float | None,
        value: str | None,
        dissent: str | None,
        evidence_ids: list[str],
        agent_id: str,
        supersedes: str | None,
    ) -> None:
        index_dirty = 1 if status == "bound" else 0
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO decision_instances (
                    id, fact_key, status, final_class, bar, confidence, value, dissent,
                    evidence_json, agent_id, supersedes, index_dirty, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    instance_id,
                    fact_key,
                    status,
                    final_class,
                    bar,
                    confidence,
                    value,
                    dissent,
                    json.dumps(evidence_ids),
                    agent_id,
                    supersedes,
                    index_dirty,
                    _utc_now(),
                ),
            )

    def bind(self, fact_key: str, decision_id: str, value: str, risk_floor: str) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO fact_bindings (fact_key, decision_id, value, risk_floor, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(fact_key) DO UPDATE SET
                    decision_id = excluded.decision_id,
                    value = excluded.value,
                    risk_floor = excluded.risk_floor,
                    updated_at = excluded.updated_at
                """,
                (fact_key, decision_id, value, risk_floor, _utc_now()),
            )

    def mark_indexed(self, decision_id: str) -> None:
        with self._connection() as conn:
            conn.execute(
                "UPDATE decision_instances SET index_dirty = 0 WHERE id = ?",
                (decision_id,),
            )

    def current_binding(self, fact_key: str) -> dict | None:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT decision_id, value FROM fact_bindings WHERE fact_key = ?",
                (fact_key,),
            ).fetchone()
        if row is None:
            return None
        return {"decision_id": row["decision_id"], "value": row["value"]}

    def instance(self, decision_id: str) -> dict | None:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT * FROM decision_instances WHERE id = ?",
                (decision_id,),
            ).fetchone()
        if row is None:
            return None
        data = dict(row)
        data["index_dirty"] = int(data["index_dirty"])
        return data

    def binding_ids(self) -> dict[str, str]:
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT fact_key, decision_id FROM fact_bindings"
            ).fetchall()
        return {row["fact_key"]: row["decision_id"] for row in rows}

    def note_use(self, decision_id: str, reward: float) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO memory_utility (decision_id, successes, trials)
                VALUES (?, ?, 1)
                ON CONFLICT(decision_id) DO UPDATE SET
                    successes = successes + excluded.successes,
                    trials = trials + 1
                """,
                (decision_id, reward),
            )

    def utilities(self) -> dict[str, tuple[float, float]]:
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT decision_id, successes, trials FROM memory_utility"
            ).fetchall()
        return {row["decision_id"]: (float(row["successes"]), float(row["trials"])) for row in rows}

    def log_recall(self, query: str, returned_ids: list[str]) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO recall_log (id, query, returned_ids_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (str(uuid4()), query, json.dumps(list(returned_ids)), _utc_now()),
            )

    def latest_recall(self) -> dict[str, object] | None:
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT query, returned_ids_json
                FROM recall_log
                ORDER BY created_at DESC, rowid DESC
                LIMIT 1
                """
            ).fetchone()
        if row is None:
            return None
        return {"query": row["query"], "returned_ids": list(json.loads(row["returned_ids_json"]))}
