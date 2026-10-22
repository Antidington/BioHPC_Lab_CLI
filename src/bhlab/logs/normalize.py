from __future__ import annotations

from pathlib import Path

from bhlab.logs.sources import parse_file, split_source
from bhlab.logs.store import Store


def source_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.exists():
        raise FileNotFoundError(f"log source not found: {path}")
    patterns = ("*.jsonl", "*.log", "*.out", "*.txt", "*.jsonl.gz", "*.log.gz")
    files: list[Path] = []
    for pattern in patterns:
        files.extend(sorted(path.glob(pattern)))
    return sorted(set(files))


def normalize(sources: list[str], db_path: Path) -> dict[str, int]:
    store = Store(db_path)
    counts: dict[str, int] = {}
    try:
        for spec in sources:
            source, path = split_source(spec)
            files = source_files(path)
            if not files:
                raise FileNotFoundError(f"no log files under {path}")
            inserted = 0
            for file in files:
                for event in parse_file(source, file):
                    if event.source == "app" and source == "app":
                        event.source = "app"
                    inserted += 1 if store.insert(event) else 0
            counts[source] = counts.get(source, 0) + inserted
    finally:
        store.close()
    return counts
