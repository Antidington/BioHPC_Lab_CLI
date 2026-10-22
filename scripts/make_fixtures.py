"""Create deterministic fixtures for tests and the acceptance demo."""

from __future__ import annotations

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
READS = ROOT / "fixtures" / "reads"
LOGS = ROOT / "fixtures" / "logs"
NORMAL = ROOT / "fixtures" / "runs" / "normal"


def write_fastq(path: Path, reads: int, length: int, seed: int) -> None:
    rng = random.Random(seed)
    bases = "ACGT"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for index in range(reads):
            seq = "".join(rng.choice(bases) for _ in range(length))
            handle.write(f"@read{index:04d}\n{seq}\n+\n{'I' * length}\n")


def event(job_id: str, event: str, params: dict, level: str = "info", message: str = "") -> dict:
    return {
        "ts": "2026-10-22T10:00:00Z",
        "source": "app",
        "job_id": job_id,
        "host": "node01",
        "event": event,
        "level": level,
        "message": message,
        "params": {key: str(value) for key, value in params.items()},
    }


def main() -> None:
    write_fastq(READS / "small.fq", 200, 120, 7)
    write_fastq(READS / "tiny.fq", 24, 60, 11)
    input_bytes = (READS / "tiny.fq").stat().st_size
    signature = {
        "app": "kmer",
        "comm": "local",
        "device": "cpu",
        "layout": "aos8",
        "input_bytes": input_bytes,
        "k": 15,
    }

    NORMAL.mkdir(parents=True, exist_ok=True)
    rng = random.Random(3)
    for index in range(10):
        job_id = f"normal-{index:03d}"
        duration = 0.62 + rng.random() * 0.16
        rows = [
            event(job_id, "run_start", {**signature, "ranks": 1}),
            event(job_id, "phase_end", {"phase": "count", "seconds": duration, "kmers": 3120}),
            event(job_id, "run_end", {
                "exit_code": 0,
                "duration_s": duration,
                "peak_rss_mb": 22.0 + rng.random() * 3.0,
                "output": "counts.tsv",
            }),
        ]
        with (NORMAL / f"{job_id}.jsonl").open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, sort_keys=True) + "\n")

    fault = [
        event("fault-001", "run_start", {**signature, "ranks": 1}),
        event("fault-001", "phase_end", {"phase": "count", "seconds": 0.71, "kmers": 3118}),
        event("fault-001", "error", {"exit_code": 137, "code": "OOM"},
              level="error", message="CUDA out of memory while allocating k-mer table"),
        event("fault-001", "run_end", {
            "exit_code": 137,
            "duration_s": 3.4,
            "peak_rss_mb": 1900.0,
            "output": "counts.tsv",
        }, level="error"),
    ]
    LOGS.mkdir(parents=True, exist_ok=True)
    with (LOGS / "fault.jsonl").open("w", encoding="utf-8") as handle:
        for row in fault:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    (LOGS / "slurm_job.out").write_text(
        "2026-10-22T10:00:01Z slurmstepd: error: Detected 1 oom-kill event(s) in StepId=9001.batch\n"
        "2026-10-22T10:00:02Z slurmd[123]: error: job 9001 exceeded memory limit\n"
        "2026-10-22T10:00:03Z slurmstepd: error: Some of your processes may have been killed\n",
        encoding="utf-8",
    )
    (LOGS / "syslog.txt").write_text(
        "Oct 22 10:00:01 node01 kernel: Out of memory: Killed process 4242 (bhlab-kmer)\n"
        "Oct 22 10:00:02 node01 kernel: oom_reaper: reaped process 4242\n",
        encoding="utf-8",
    )
    print(f"fixtures written under {ROOT / 'fixtures'}")


if __name__ == "__main__":
    main()
