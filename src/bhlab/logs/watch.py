from __future__ import annotations

import json
import time
import urllib.request
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from bhlab.logs import baseline
from bhlab.logs.rules import Rule, RuleEngine
from bhlab.logs.schema import LogEvent
from bhlab.logs.sources import parse_line, read_lines, split_source
from bhlab.logs.store import Store


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Tailer:
    def __init__(self, path: Path, source: str, from_end: bool = True):
        self.path = path
        self.source = source
        self.offset = path.stat().st_size if from_end and path.exists() else 0
        self.buffer = ""

    def poll(self) -> list[LogEvent]:
        if not self.path.exists():
            return []
        size = self.path.stat().st_size
        if size < self.offset:
            self.offset = 0
            self.buffer = ""
        if size == self.offset:
            return []
        with self.path.open("rb") as handle:
            handle.seek(self.offset)
            data = handle.read()
            self.offset = handle.tell()
        self.buffer += data.decode("utf-8", errors="replace")
        lines = self.buffer.split("\n")
        self.buffer = lines.pop()
        fallback = datetime.now(timezone.utc)
        events: list[LogEvent] = []
        for line in lines:
            events.extend(parse_line(self.source, line, self.path, fallback))
        return events


class Watcher:
    def __init__(
        self,
        store: Store,
        rules: list[Rule],
        model: dict,
        window: int = 50,
        dedupe_seconds: int = 300,
        webhook: str = "",
        alert_log: Path | None = None,
        echo: Callable[[str], None] = print,
    ):
        self.store = store
        self.engine = RuleEngine(rules, model)
        self.window = window
        self.dedupe_seconds = dedupe_seconds
        self.webhook = webhook
        self.alert_log = alert_log or (store.path.parent / "alerts.jsonl")
        self.echo = echo
        self.history: dict[str, list[LogEvent]] = {}
        self.starts: dict[str, LogEvent] = {}
        self.last_seen: dict[str, str] = {}
        self.ended: set[str] = set()
        self.last_alert: dict[tuple[str, str], float] = {}
        self.alerts: list[dict] = []

    def ingest(self, event: LogEvent) -> list[dict]:
        self.store.insert(event)
        if event.event == "run_start":
            self.starts[event.job_id] = event
        self.last_seen[event.job_id] = event.ts
        buffer = self.history.setdefault(event.job_id, [])
        buffer.append(event)
        if len(buffer) > self.window:
            del buffer[: len(buffer) - self.window]

        summary = None
        if event.event == "run_end":
            self.ended.add(event.job_id)
            start = self.starts.get(event.job_id)
            events = ([start] if start and start not in buffer else []) + buffer
            collected = baseline.collect(events)
            summary = next((item for item in collected if item.job_id == event.job_id), None)

        emitted = []
        for alert in self.engine.evaluate_event(event, list(buffer), summary):
            alert = self._emit(alert)
            if alert:
                emitted.append(alert)
        return emitted

    def _emit(self, alert: dict) -> dict | None:
        key = (alert["job_id"], alert["rule_id"])
        now = time.time()
        last = self.last_alert.get(key)
        if last is not None and now - last < self.dedupe_seconds:
            return None
        self.last_alert[key] = now
        alert["id"] = self.store.insert_alert(alert)
        self.alerts.append(alert)
        self.alert_log.parent.mkdir(parents=True, exist_ok=True)
        with self.alert_log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(alert, sort_keys=True, ensure_ascii=False) + "\n")
        self.echo(
            f"[{alert['severity']}] job={alert['job_id']} rule={alert['rule_id']} "
            f"{alert['message']}"
        )
        if self.webhook:
            try:
                payload = json.dumps(alert).encode("utf-8")
                request = urllib.request.Request(
                    self.webhook, data=payload,
                    headers={"Content-Type": "application/json"}, method="POST",
                )
                urllib.request.urlopen(request, timeout=5).read()
            except Exception as error:  # pragma: no cover - external sink
                self.echo(f"webhook failed: {error}")
        return alert

    def replay(self, path: Path, delay: float = 0.0) -> list[dict]:
        events = []
        for line in read_lines(path):
            if not line.strip():
                continue
            fallback = datetime.now(timezone.utc)
            events.extend(parse_line("app", line, path, fallback))
        for event in events:
            self.ingest(event)
            if delay:
                time.sleep(delay)
        return self.alerts

    def follow(self, sources: list[str], interval: float = 1.0,
               max_iterations: int | None = None) -> list[dict]:
        tailers = []
        for spec in sources:
            source, path = split_source(spec)
            tailers.append(Tailer(path, source, from_end=True))
        self.echo(f"watching {len(tailers)} log source(s)")
        iterations = 0
        try:
            while max_iterations is None or iterations < max_iterations:
                for tailer in tailers:
                    for event in tailer.poll():
                        self.ingest(event)
                self._check_silence()
                iterations += 1
                if max_iterations is None or iterations < max_iterations:
                    time.sleep(interval)
        except KeyboardInterrupt:
            self.echo("watch stopped")
        return self.alerts

    def _check_silence(self) -> None:
        now = datetime.now(timezone.utc)
        silence_rules = [rule for rule in self.engine.rules if rule.type == "silence"]
        if not silence_rules:
            return
        for job_id, start in self.starts.items():
            if job_id in self.ended:
                continue
            last = self.last_seen.get(job_id, start.ts)
            try:
                seen = datetime.fromisoformat(last.replace("Z", "+00:00"))
            except ValueError:
                continue
            gap = (now - seen).total_seconds()
            for rule in silence_rules:
                if gap <= rule.max_gap_s:
                    continue
                history = self.history.get(job_id, [start])
                alert = {
                    "ts": _now(),
                    "rule_id": rule.id,
                    "job_id": job_id,
                    "severity": rule.severity,
                    "message": f"no event for {int(gap)}s (limit {rule.max_gap_s}s)",
                    "evidence": [event.to_dict() for event in history],
                }
                self._emit(alert)
