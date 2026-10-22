from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

REQUIRED = ("ts", "source", "job_id", "host", "event", "level")


class SchemaError(ValueError):
    pass


@dataclass
class LogEvent:
    ts: str
    source: str
    job_id: str
    host: str
    event: str
    level: str = "info"
    message: str = ""
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict) -> LogEvent:
        missing = [key for key in REQUIRED if not data.get(key)]
        if missing:
            raise SchemaError(f"missing required fields: {', '.join(missing)}")
        ts = str(data["ts"])
        try:
            datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError as error:
            raise SchemaError(f"ts is not ISO8601: {ts}") from error
        params = data.get("params") or {}
        if not isinstance(params, dict):
            raise SchemaError("params must be an object")
        return cls(
            ts=ts,
            source=str(data["source"]),
            job_id=str(data["job_id"]),
            host=str(data["host"]),
            event=str(data["event"]),
            level=str(data.get("level", "info")),
            message=str(data.get("message", "")),
            params=params,
        )

    @classmethod
    def from_json(cls, line: str) -> LogEvent:
        try:
            data = json.loads(line)
        except json.JSONDecodeError as error:
            raise SchemaError(f"invalid JSON: {error}") from error
        if not isinstance(data, dict):
            raise SchemaError("event must be a JSON object")
        return cls.from_dict(data)
