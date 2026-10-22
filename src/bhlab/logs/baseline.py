from __future__ import annotations

import json
import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from bhlab.logs.schema import LogEvent


def _float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def size_bucket(value: float) -> str:
    if value <= 0:
        return "unknown"
    power = math.floor(math.log10(value))
    return f"1e{power}-1e{power + 1}"


def signature_from(start: LogEvent) -> dict:
    params = start.params
    return {
        "app": params.get("app", "unknown"),
        "comm": params.get("comm", "unknown"),
        "device": params.get("device", "unknown"),
        "layout": params.get("layout", "unknown"),
        "k": params.get("k", "unknown"),
        "size": size_bucket(_float(params.get("input_bytes", 0))),
    }


def signature_key(signature: dict) -> str:
    return "|".join(f"{key}={signature[key]}" for key in sorted(signature))


@dataclass
class JobSummary:
    job_id: str
    signature: dict
    duration_s: float
    input_bytes: float
    peak_rss_mb: float
    exit_code: int
    events: list[LogEvent] = field(default_factory=list)

    @property
    def duration_per_gb(self) -> float:
        return self.duration_s / max(self.input_bytes / 1e9, 1e-9)

    @property
    def rss_per_gb(self) -> float:
        return self.peak_rss_mb / max(self.input_bytes / 1e9, 1e-9)


def collect(events: list[LogEvent]) -> list[JobSummary]:
    grouped: dict[str, list[LogEvent]] = {}
    for event in events:
        grouped.setdefault(event.job_id, []).append(event)
    summaries: list[JobSummary] = []
    for job_id, job_events in grouped.items():
        starts = [event for event in job_events if event.event == "run_start"]
        ends = [event for event in job_events if event.event == "run_end"]
        if not starts or not ends:
            continue
        start = starts[0]
        end = ends[-1]
        duration = _float(end.params.get("duration_s"))
        if duration <= 0:
            try:
                begin = datetime.fromisoformat(start.ts.replace("Z", "+00:00"))
                finish = datetime.fromisoformat(end.ts.replace("Z", "+00:00"))
                duration = max((finish - begin).total_seconds(), 0.0)
            except ValueError:
                duration = 0.0
        summaries.append(JobSummary(
            job_id=job_id,
            signature=signature_from(start),
            duration_s=duration,
            input_bytes=_float(start.params.get("input_bytes")),
            peak_rss_mb=_float(end.params.get("peak_rss_mb")),
            exit_code=int(_float(end.params.get("exit_code"))),
            events=job_events,
        ))
    return summaries


def _stats(values: list[float], n: int) -> dict:
    ordered = sorted(values)
    median = statistics.median(ordered)
    mad = statistics.median([abs(value - median) for value in ordered])
    p95 = ordered[min(len(ordered) - 1, int(0.95 * (len(ordered) - 1)))]
    return {"n": n, "median": median, "mad": mad, "p95": p95}


def build(events: list[LogEvent], min_samples: int = 8) -> dict:
    groups: dict[str, list[JobSummary]] = {}
    for summary in collect(events):
        groups.setdefault(signature_key(summary.signature), []).append(summary)
    models = {}
    for key, summaries in sorted(groups.items()):
        durations = [summary.duration_per_gb for summary in summaries if summary.input_bytes > 0]
        rss = [summary.rss_per_gb for summary in summaries if summary.input_bytes > 0]
        if not durations:
            continue
        model = {
            "n": len(summaries),
            "min_samples": min_samples,
            "insufficient": len(summaries) < min_samples,
            "metrics": {
                "duration_per_gb": _stats(durations, len(summaries)),
                "rss_per_gb": _stats(rss, len(summaries)),
            },
        }
        models[key] = model
    return {"generated_at": _iso_now(), "min_samples": min_samples, "models": models}


def load_history(path: Path) -> list[LogEvent]:
    events: list[LogEvent] = []
    files = sorted(path.glob("**/*.jsonl")) if path.is_dir() else [path]
    for file in files:
        for line in file.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    events.append(LogEvent.from_json(line))
                except ValueError:
                    continue
    return events


def write(model: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(model, indent=2, sort_keys=True), encoding="utf-8")
    return path


def load(path: Path) -> dict:
    if not path.exists():
        return {"models": {}, "min_samples": 8}
    return json.loads(path.read_text(encoding="utf-8"))


def _robust_z(value: float, stats: dict) -> float:
    mad = stats.get("mad", 0.0)
    if mad <= 0:
        return 0.0
    return 0.6745 * (value - stats["median"]) / mad


def evaluate(model: dict, summary: JobSummary, multiplier: float = 1.5) -> list[dict]:
    key = signature_key(summary.signature)
    entry = model.get("models", {}).get(key)
    if not entry or entry.get("insufficient"):
        return []
    findings = []
    values = {
        "duration_per_gb": summary.duration_per_gb,
        "rss_per_gb": summary.rss_per_gb,
    }
    for metric, value in values.items():
        stats = entry["metrics"].get(metric)
        if not stats or stats["n"] < model.get("min_samples", 8):
            continue
        z = _robust_z(value, stats)
        threshold = stats["p95"] * multiplier
        if stats["mad"] <= 0:
            triggered = value > stats["median"] * multiplier
        else:
            triggered = value > threshold or z > 3.5
        if triggered:
            findings.append({
                "metric": metric,
                "value": value,
                "median": stats["median"],
                "p95": stats["p95"],
                "z": z,
                "signature": key,
            })
    return findings
