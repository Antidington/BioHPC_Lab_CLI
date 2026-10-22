from __future__ import annotations

import csv
import itertools
import json
import platform
import statistics
from datetime import datetime, timezone
from pathlib import Path

from bhlab.capabilities import detect
from bhlab.config import Config
from bhlab.planner import PlanError, RunSpec
from bhlab.runner import RunnerError, run, run_end_params


class BenchError(RuntimeError):
    pass


def parse_matrix(value: str) -> dict[str, list[str]]:
    matrix: dict[str, list[str]] = {}
    for group in value.split(";"):
        group = group.strip()
        if not group:
            continue
        if "=" not in group:
            raise BenchError(f"invalid matrix group '{group}', expected key=value1,value2")
        key, values = group.split("=", 1)
        matrix[key.strip()] = [item.strip() for item in values.split(",") if item.strip()]
    if not matrix:
        matrix = {"comm": ["local"], "device": ["cpu"], "layout": ["aos8"]}
    return matrix


def _combos(matrix: dict[str, list[str]]) -> list[dict[str, str]]:
    keys = list(matrix)
    return [dict(zip(keys, values)) for values in itertools.product(*(matrix[key] for key in keys))]


def _manifest(config: Config, matrix: dict[str, list[str]], repeat: int) -> dict:
    caps = detect()
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "host": platform.node(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "matrix": matrix,
        "repeat": repeat,
        "capabilities": caps.to_dict(),
        "root": str(config.root),
    }


def bench(
    config: Config,
    input_path: Path,
    out_dir: Path,
    matrix: dict[str, list[str]],
    repeat: int = 3,
    k: int = 21,
    app: str = "kmer",
    allow_missing: bool = False,
) -> list[dict]:
    caps = detect()
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for combo in _combos(matrix):
        for repetition in range(repeat):
            comm = combo.get("comm", "local")
            device = combo.get("device", "cpu")
            layout = combo.get("layout", "auto")
            nodes = int(combo.get("nodes", "1"))
            tag = f"{app}-{comm}-{device}-{layout}-n{nodes}-r{repetition}"
            run_dir = out_dir / "runs" / tag
            spec = RunSpec(
                app=app,
                input=input_path,
                output=run_dir / "counts.tsv",
                comm=comm,
                device=device,
                layout=layout,
                nodes=nodes,
                ranks_per_node=int(combo.get("ranks", "1")),
                threads=int(combo.get("threads", "1")),
                k=k,
                job_id=tag,
            )
            try:
                result = run(spec, config, caps)
                if result.returncode != 0:
                    raise BenchError(result.stderr or f"run failed with {result.returncode}")
            except (PlanError, RunnerError, BenchError) as error:
                if not allow_missing:
                    raise
                rows.append({
                    "tag": tag, "comm": comm, "device": device, "layout": layout,
                    "nodes": nodes, "repeat": repetition, "status": "skipped",
                    "duration_s": 0.0, "throughput_mb_s": 0.0, "checksum": "",
                    "note": str(error),
                })
                continue
            params = run_end_params(spec.events)
            duration = float(params.get("duration_s", result.duration_s))
            size_mb = input_path.stat().st_size / 1e6
            throughput = size_mb / duration if duration > 0 else 0.0
            rows.append({
                "tag": tag, "comm": comm, "device": device, "layout": layout,
                "nodes": nodes, "repeat": repetition, "status": "ok",
                "duration_s": duration, "throughput_mb_s": throughput,
                "checksum": result.checksum, "note": "",
            })
    _write_csv(out_dir / "bench.csv", rows)
    (out_dir / "manifest.json").write_text(
        json.dumps(_manifest(config, matrix, repeat), indent=2, sort_keys=True), encoding="utf-8",
    )
    _summarize(rows)
    return rows


def _write_csv(path: Path, rows: list[dict]) -> None:
    fields = ["tag", "comm", "device", "layout", "nodes", "repeat", "status",
              "duration_s", "throughput_mb_s", "checksum", "note"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _summarize(rows: list[dict]) -> None:
    groups: dict[tuple, list[dict]] = {}
    for row in rows:
        if row["status"] != "ok":
            continue
        key = (row["comm"], row["device"], row["layout"], row["nodes"])
        groups.setdefault(key, []).append(row)
    print(f"{'comm':8} {'device':6} {'layout':6} {'nodes':5} {'median MB/s':>12} {'checksum':10}")
    for key, values in sorted(groups.items()):
        median = statistics.median(value["throughput_mb_s"] for value in values)
        checksum = values[0]["checksum"][:10]
        print(f"{key[0]:8} {key[1]:6} {key[2]:6} {key[3]:<5} {median:12.3f} {checksum:10}")
