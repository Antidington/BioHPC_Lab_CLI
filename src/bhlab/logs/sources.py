from __future__ import annotations

import gzip
import json
import re
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

from bhlab.logs.schema import LogEvent, SchemaError

SOURCE_NAMES = {"app", "slurm", "syslog", "text"}
ISO_PREFIX = re.compile(r"^\[?(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})?)\]?\s*")
SYSLOG_PREFIX = re.compile(
    r"^([A-Z][a-z]{2})\s+(\d{1,2})\s+(\d{2}:\d{2}:\d{2})\s+(\S+)\s+([^:]+):\s*(.*)$"
)
JOB_RE = re.compile(r"(?:job|JobID|StepId)[=:\s]+(\d+)", re.IGNORECASE)
PID_RE = re.compile(r"\[(\d+)\]")


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_timestamp(token: str, fallback: datetime) -> str:
    cleaned = token.strip().strip("[]")
    if not cleaned:
        return _iso(fallback)
    try:
        if cleaned.endswith("Z"):
            return _iso(datetime.fromisoformat(cleaned.replace("Z", "+00:00")))
        value = datetime.fromisoformat(cleaned)
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return _iso(value)
    except ValueError:
        return _iso(fallback)


def infer_level(text: str) -> str:
    lowered = text.lower()
    if any(word in lowered for word in ("oom", "out of memory", "killed", "fatal", "abort", "error", "failed")):
        return "error"
    if "warn" in lowered:
        return "warning"
    return "info"


def infer_event(text: str) -> str:
    lowered = text.lower()
    if "out of memory" in lowered or "oom" in lowered:
        return "oom_kill"
    if "cuda" in lowered:
        return "cuda_error"
    if "timeout" in lowered or "timed out" in lowered:
        return "timeout"
    if "killed" in lowered:
        return "killed"
    return "log"


def _job_from(text: str, fallback: str) -> str:
    match = JOB_RE.search(text)
    return match.group(1) if match else fallback


def parse_app_line(line: str, path: Path, fallback: datetime) -> list[LogEvent]:
    line = line.strip()
    if not line:
        return []
    try:
        data = json.loads(line)
        if not isinstance(data, dict):
            raise SchemaError("event must be an object")
        data.setdefault("source", "app")
        data.setdefault("job_id", path.stem)
        data.setdefault("host", "unknown")
        data.setdefault("event", "app_log")
        data.setdefault("level", "info")
        data.setdefault("message", "")
        data.setdefault("ts", _iso(fallback))
        return [LogEvent.from_dict(data)]
    except (json.JSONDecodeError, SchemaError):
        return [LogEvent(
            ts=_iso(fallback), source="app", job_id=path.stem, host="unknown",
            event="app_log", level=infer_level(line), message=line,
        )]


def _sacct_records(data) -> list[dict]:
    if isinstance(data, dict):
        jobs = data.get("jobs")
        if isinstance(jobs, list):
            return [job for job in jobs if isinstance(job, dict)]
        return [data]
    if isinstance(data, list):
        return [job for job in data if isinstance(job, dict)]
    return []


def parse_slurm_line(line: str, path: Path, fallback: datetime) -> list[LogEvent]:
    line = line.strip()
    if not line:
        return []
    if line.startswith(("{", "[")):
        try:
            data = json.loads(line)
            events: list[LogEvent] = []
            for record in _sacct_records(data):
                job_id = str(record.get("job_id") or record.get("JobID") or path.stem)
                state = str(record.get("state") or record.get("State") or "unknown")
                exit_code = record.get("exit_code") or record.get("ExitCode") or ""
                event = f"slurm_{state.lower()}"
                events.append(LogEvent(
                    ts=_iso(fallback), source="slurm", job_id=job_id, host="slurm",
                    event=event, level=infer_level(state), message=f"state={state}",
                    params={"state": state, "exit_code": str(exit_code)},
                ))
            return events
        except json.JSONDecodeError:
            pass
    match = ISO_PREFIX.match(line)
    ts = parse_timestamp(match.group(1), fallback) if match else _iso(fallback)
    body = line[match.end():] if match else line
    job_id = _job_from(body, path.stem)
    level = infer_level(body)
    event = infer_event(body)
    if "exceeded memory" in body.lower():
        event = "memory_limit"
    if "cancelled" in body.lower():
        event = "cancelled"
    return [LogEvent(
        ts=ts, source="slurm", job_id=job_id, host="slurm", event=event,
        level=level, message=body,
    )]


def parse_text_line(line: str, path: Path, fallback: datetime) -> list[LogEvent]:
    line = line.strip()
    if not line:
        return []
    host = "unknown"
    program = "system"
    message = line
    ts = _iso(fallback)
    syslog = SYSLOG_PREFIX.match(line)
    iso = ISO_PREFIX.match(line)
    if syslog:
        month, day, clock, host, program, message = syslog.groups()
        year = fallback.year
        try:
            parsed = datetime.strptime(f"{year} {month} {day} {clock}", "%Y %b %d %H:%M:%S")
            ts = _iso(parsed.replace(tzinfo=timezone.utc))
        except ValueError:
            ts = _iso(fallback)
    elif iso:
        ts = parse_timestamp(iso.group(1), fallback)
        message = line[iso.end():]
    level = infer_level(message)
    event = infer_event(message)
    pid_match = PID_RE.search(program)
    params = {"program": program}
    if pid_match:
        params["pid"] = pid_match.group(1)
    return [LogEvent(
        ts=ts, source="text" if path.suffix == ".txt" else "syslog",
        job_id=_job_from(message, "system"), host=host, event=event, level=level,
        message=message, params=params,
    )]


def parse_line(source: str, line: str, path: Path, fallback: datetime) -> list[LogEvent]:
    if source == "app":
        return parse_app_line(line, path, fallback)
    if source == "slurm":
        return parse_slurm_line(line, path, fallback)
    events = parse_text_line(line, path, fallback)
    for event in events:
        event.source = source
    return events


def read_lines(path: Path) -> Iterator[str]:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
            yield from handle
    else:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            yield from handle


def parse_file(source: str, path: Path) -> list[LogEvent]:
    fallback = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    events: list[LogEvent] = []
    for line in read_lines(path):
        events.extend(parse_line(source, line, path, fallback))
    return events


def split_source(spec: str) -> tuple[str, Path]:
    if ":" in spec:
        prefix, remainder = spec.split(":", 1)
        if prefix in SOURCE_NAMES:
            return prefix, Path(remainder)
    path = Path(spec)
    name = path.name.lower()
    if "slurm" in name or path.suffix == ".out":
        return "slurm", path
    if "syslog" in name or "dmesg" in name:
        return "syslog", path
    return "app", path
