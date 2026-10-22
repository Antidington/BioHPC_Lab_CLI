from pathlib import Path

import pytest

from bhlab.logs import baseline
from bhlab.logs.keywords import extract
from bhlab.logs.normalize import normalize
from bhlab.logs.rules import load_rules
from bhlab.logs.schema import LogEvent, SchemaError
from bhlab.logs.store import Store
from bhlab.logs.watch import Watcher

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"


def test_schema_roundtrip() -> None:
    event = LogEvent.from_json(
        '{"ts":"2026-10-22T10:00:00Z","source":"app","job_id":"j1",'
        '"host":"h","event":"run_start","level":"info","params":{"k":"15"}}'
    )
    assert event.job_id == "j1"
    assert LogEvent.from_json(event.to_json()).params["k"] == "15"


def test_schema_rejects_bad_time() -> None:
    with pytest.raises(SchemaError):
        LogEvent.from_dict({
            "ts": "yesterday", "source": "app", "job_id": "j", "host": "h",
            "event": "x", "level": "info",
        })


def test_normalize_three_sources(tmp_path: Path) -> None:
    counts = normalize(
        [
            f"app:{FIXTURES / 'logs' / 'fault.jsonl'}",
            f"slurm:{FIXTURES / 'logs' / 'slurm_job.out'}",
            f"syslog:{FIXTURES / 'logs' / 'syslog.txt'}",
        ],
        tmp_path / "events.db",
    )
    assert counts["app"] >= 3
    assert counts["slurm"] >= 1
    assert counts["syslog"] >= 1
    store = Store(tmp_path / "events.db")
    stats = store.stats()
    store.close()
    assert stats["by_source"]["app"] >= 3
    assert stats["by_source"]["slurm"] >= 1
    assert stats["by_source"]["syslog"] >= 1


def test_query_and_keywords(tmp_path: Path) -> None:
    db = tmp_path / "events.db"
    normalize([f"app:{FIXTURES / 'logs' / 'fault.jsonl'}"], db)
    store = Store(db)
    hits = store.query(grep="OOM", sort="ts")
    assert hits
    assert all("OOM" in (item.message + str(item.params)) for item in hits)
    words = extract(store, "fault-001", 10)
    store.close()
    assert any(item["token"] in {"oom", "memory", "cuda"} for item in words)


def test_baseline_and_evaluate() -> None:
    events = baseline.load_history(FIXTURES / "runs" / "normal")
    model = baseline.build(events, 8)
    assert len(model["models"]) == 1
    entry = next(iter(model["models"].values()))
    assert entry["n"] == 10
    assert entry["insufficient"] is False

    fault = baseline.load_history(FIXTURES / "logs" / "fault.jsonl")
    summary = baseline.collect(fault)[0]
    findings = baseline.evaluate(model, summary)
    assert any(item["metric"] == "duration_per_gb" for item in findings)


def test_watch_replay_emits_alerts(tmp_path: Path) -> None:
    db = tmp_path / "events.db"
    normalize([f"app:{FIXTURES / 'logs' / 'fault.jsonl'}"], db)
    model = baseline.build(baseline.load_history(FIXTURES / "runs" / "normal"), 8)
    store = Store(db)
    watcher = Watcher(
        store, load_rules(ROOT / "rules" / "default.toml"), model,
        window=50, dedupe_seconds=0, echo=lambda _: None,
    )
    alerts = watcher.replay(FIXTURES / "logs" / "fault.jsonl")
    store.close()
    assert {alert["rule_id"] for alert in alerts} >= {"oom", "slow", "exit"}
    assert any(len(alert["evidence"]) >= 2 for alert in alerts)
