from __future__ import annotations

import json
import re
from collections import Counter

from bhlab.logs.store import Store

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{2,}")
STOPWORDS = {
    "the", "and", "for", "with", "from", "this", "that", "was", "were", "has", "have",
    "job", "step", "error", "info", "warning", "local", "run", "node", "process", "some",
    "your", "may", "been", "into", "while", "after", "before", "not", "but", "all", "can",
}
ANOMALY_WORDS = {
    "oom", "out_of_memory", "cuda", "timeout", "timed", "killed", "abort", "aborted",
    "failed", "failure", "denied", "segfault", "panic", "exceeded", "memory",
}


def _tokens(event) -> list[str]:
    text = " ".join([event.event, event.message, json.dumps(event.params, sort_keys=True)])
    return [token.lower() for token in TOKEN_RE.findall(text) if token.lower() not in STOPWORDS]


def extract(store: Store, job: str = "", top: int = 20) -> list[dict]:
    target = store.query(job=job, limit=100000) if job else store.query(limit=100000)
    background = store.query(limit=100000)
    target_counter: Counter[str] = Counter()
    background_counter: Counter[str] = Counter()
    target_jobs = {event.job_id for event in target}
    for event in target:
        target_counter.update(_tokens(event))
    for event in background:
        if event.job_id not in target_jobs:
            background_counter.update(_tokens(event))
    target_total = max(sum(target_counter.values()), 1)
    background_total = max(sum(background_counter.values()), 1)
    scored = []
    for token, count in target_counter.items():
        target_rate = count / target_total
        background_rate = (background_counter[token] + 1) / (background_total + len(target_counter))
        score = target_rate / background_rate
        scored.append({
            "token": token,
            "count": count,
            "score": round(score, 3),
            "anomaly": token in ANOMALY_WORDS,
        })
    scored.sort(key=lambda row: (row["anomaly"], row["score"], row["count"]), reverse=True)
    return scored[:top]
