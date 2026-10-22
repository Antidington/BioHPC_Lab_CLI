from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from bhlab.logs import baseline
from bhlab.logs.schema import LogEvent

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10
    import tomli as tomllib


@dataclass
class Rule:
    id: str
    type: str
    severity: str = "warning"
    keywords: list[str] = field(default_factory=list)
    max_gap_s: int = 120
    max_errors: int = 3
    multiplier: float = 1.5


def load_rules(path: Path) -> list[Rule]:
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    rules = []
    for item in data.get("rules", []):
        rules.append(Rule(
            id=str(item["id"]),
            type=str(item["type"]),
            severity=str(item.get("severity", "warning")),
            keywords=[str(value).lower() for value in item.get("keywords", [])],
            max_gap_s=int(item.get("max_gap_s", 120)),
            max_errors=int(item.get("max_errors", 3)),
            multiplier=float(item.get("multiplier", 1.5)),
        ))
    return rules


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _alert(rule: Rule, event: LogEvent, message: str, evidence: list[LogEvent]) -> dict:
    return {
        "ts": _now(),
        "rule_id": rule.id,
        "job_id": event.job_id,
        "severity": rule.severity,
        "message": message,
        "evidence": [item.to_dict() for item in evidence],
    }


class RuleEngine:
    def __init__(self, rules: list[Rule], model: dict):
        self.rules = rules
        self.model = model
        self.error_counts: dict[str, int] = {}

    def evaluate_event(self, event: LogEvent, history: list[LogEvent],
                       summary: baseline.JobSummary | None = None) -> list[dict]:
        alerts = []
        text = " ".join([
            event.event, event.message,
            json.dumps(event.params, sort_keys=True),
        ]).lower()
        for rule in self.rules:
            if rule.type == "keyword":
                hits = [word for word in rule.keywords if word in text]
                if hits:
                    alerts.append(_alert(
                        rule, event, f"keyword matched: {', '.join(hits)}", history,
                    ))
            elif rule.type == "exit_code" and event.event == "run_end":
                try:
                    code = int(float(event.params.get("exit_code", 0)))
                except (TypeError, ValueError):
                    code = 0
                if code != 0:
                    alerts.append(_alert(rule, event, f"non-zero exit code {code}", history))
            elif rule.type == "retry" and event.level == "error":
                self.error_counts[event.job_id] = self.error_counts.get(event.job_id, 0) + 1
                if self.error_counts[event.job_id] > rule.max_errors:
                    alerts.append(_alert(
                        rule, event,
                        f"error count {self.error_counts[event.job_id]} exceeded {rule.max_errors}",
                        history,
                    ))
            elif rule.type == "baseline" and event.event == "run_end" and summary is not None:
                findings = baseline.evaluate(self.model, summary, rule.multiplier)
                if findings:
                    detail = "; ".join(
                        f"{item['metric']}={item['value']:.3g} (p95={item['p95']:.3g}, z={item['z']:.2f})"
                        for item in findings
                    )
                    alerts.append(_alert(rule, event, f"baseline deviation: {detail}", history))
        return alerts
