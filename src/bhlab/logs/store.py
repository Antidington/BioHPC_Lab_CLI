from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from bhlab.logs.schema import LogEvent

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  source TEXT NOT NULL,
  job_id TEXT NOT NULL,
  host TEXT NOT NULL,
  event TEXT NOT NULL,
  level TEXT NOT NULL,
  message TEXT NOT NULL DEFAULT '',
  params TEXT NOT NULL DEFAULT '{}',
  UNIQUE(ts, source, job_id, event, message, params)
);
CREATE INDEX IF NOT EXISTS idx_events_job_ts ON events(job_id, ts);
CREATE INDEX IF NOT EXISTS idx_events_source ON events(source);
CREATE INDEX IF NOT EXISTS idx_events_event ON events(event);
CREATE TABLE IF NOT EXISTS alerts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  rule_id TEXT NOT NULL,
  job_id TEXT NOT NULL,
  severity TEXT NOT NULL,
  message TEXT NOT NULL,
  evidence TEXT NOT NULL DEFAULT '[]'
);
"""


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def insert(self, event: LogEvent) -> bool:
        cursor = self.conn.execute(
            """INSERT OR IGNORE INTO events
               (ts, source, job_id, host, event, level, message, params)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event.ts,
                event.source,
                event.job_id,
                event.host,
                event.event,
                event.level,
                event.message,
                json.dumps(event.params, sort_keys=True, ensure_ascii=False),
            ),
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def insert_many(self, events: Iterable[LogEvent]) -> int:
        count = 0
        for event in events:
            if self.insert(event):
                count += 1
        return count

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> LogEvent:
        return LogEvent(
            ts=row["ts"],
            source=row["source"],
            job_id=row["job_id"],
            host=row["host"],
            event=row["event"],
            level=row["level"],
            message=row["message"],
            params=json.loads(row["params"]),
        )

    def query(
        self,
        job: str = "",
        source: str = "",
        event: str = "",
        level: str = "",
        grep: str = "",
        since: str = "",
        until: str = "",
        sort: str = "ts",
        limit: int = 100,
    ) -> list[LogEvent]:
        clauses: list[str] = []
        values: list[Any] = []
        if job:
            clauses.append("job_id = ?")
            values.append(job)
        if source:
            clauses.append("source = ?")
            values.append(source)
        if event:
            clauses.append("event = ?")
            values.append(event)
        if level:
            clauses.append("level = ?")
            values.append(level)
        if since:
            clauses.append("ts >= ?")
            values.append(since)
        if until:
            clauses.append("ts <= ?")
            values.append(until)
        if grep:
            clauses.append("(message LIKE ? OR event LIKE ? OR params LIKE ?)")
            pattern = f"%{grep}%"
            values.extend([pattern, pattern, pattern])
        order = "DESC" if sort.startswith("-") else "ASC"
        column = sort.lstrip("-")
        if column not in {"ts", "id", "level", "event"}:
            column = "ts"
        sql = "SELECT * FROM events"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += f" ORDER BY {column} {order}, id {order} LIMIT ?"
        values.append(limit)
        return [self._row_to_event(row) for row in self.conn.execute(sql, values)]

    def recent_for_job(self, job_id: str, limit: int = 50) -> list[LogEvent]:
        rows = self.conn.execute(
            "SELECT * FROM events WHERE job_id = ? ORDER BY ts ASC, id ASC", (job_id,)
        ).fetchall()
        return [self._row_to_event(row) for row in rows[-limit:]]

    def stats(self) -> dict:
        by_source = {
            row["source"]: row["count"]
            for row in self.conn.execute(
                "SELECT source, COUNT(*) AS count FROM events GROUP BY source ORDER BY source"
            )
        }
        by_level = {
            row["level"]: row["count"]
            for row in self.conn.execute(
                "SELECT level, COUNT(*) AS count FROM events GROUP BY level ORDER BY level"
            )
        }
        total = self.conn.execute("SELECT COUNT(*) AS count FROM events").fetchone()["count"]
        alerts = self.conn.execute("SELECT COUNT(*) AS count FROM alerts").fetchone()["count"]
        return {"total": total, "by_source": by_source, "by_level": by_level, "alerts": alerts}

    def jobs(self) -> list[str]:
        return [
            row["job_id"]
            for row in self.conn.execute("SELECT DISTINCT job_id FROM events ORDER BY job_id")
        ]

    def insert_alert(self, alert: dict) -> int:
        cursor = self.conn.execute(
            """INSERT INTO alerts (ts, rule_id, job_id, severity, message, evidence)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                alert["ts"],
                alert["rule_id"],
                alert["job_id"],
                alert["severity"],
                alert["message"],
                json.dumps(alert["evidence"], sort_keys=True, ensure_ascii=False),
            ),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def list_alerts(self, limit: int = 50) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]

    def get_alert(self, alert_id: int) -> dict | None:
        row = self.conn.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,)).fetchone()
        if row is None:
            return None
        data = dict(row)
        data["evidence"] = json.loads(data["evidence"])
        return data

    def export_jsonl(self, path: Path, events: Iterable[LogEvent]) -> int:
        path.parent.mkdir(parents=True, exist_ok=True)
        count = 0
        with path.open("w", encoding="utf-8") as handle:
            for event in events:
                handle.write(event.to_json() + "\n")
                count += 1
        return count
