from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from bhlab.capabilities import Capabilities, detect
from bhlab.config import Config
from bhlab.planner import LaunchPlan, RunSpec, resolve


class RunnerError(RuntimeError):
    pass


@dataclass
class RunResult:
    plan: LaunchPlan
    returncode: int
    stdout: str
    stderr: str
    duration_s: float
    checksum: str = ""
    run_json: Path | None = None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(spec: RunSpec, config: Config, caps: Capabilities | None = None,
        check_binary: bool = True) -> RunResult:
    caps = caps or detect()
    plan = resolve(spec, config, caps)
    plan.spec.output.parent.mkdir(parents=True, exist_ok=True)
    if plan.spec.events is not None:
        plan.spec.events.parent.mkdir(parents=True, exist_ok=True)
    if spec.emit_slurm:
        path = Path(spec.emit_slurm)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(plan.slurm_script(config.root), encoding="utf-8")
        return RunResult(plan=plan, returncode=0, stdout=str(path), stderr="", duration_s=0.0)
    if check_binary and not plan.binary.exists():
        raise RunnerError(
            f"binary not found: {plan.binary}. Run 'bhlab build --platform {config.platform}' first."
        )
    env = os.environ.copy()
    env.update(plan.env)
    started = _now()
    start = time.perf_counter()
    result = subprocess.run(plan.argv, check=False, cwd=config.root, env=env,
                            capture_output=True, text=True)
    duration = time.perf_counter() - start
    finished = _now()
    checksum = ""
    if spec.output.exists() and spec.output.is_file():
        checksum = sha256_file(spec.output)
    record = {
        "started": started,
        "finished": finished,
        "duration_s": duration,
        "returncode": result.returncode,
        "command": plan.command,
        "reason": plan.reason,
        "checksum": checksum,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "plan": plan.to_dict(),
    }
    run_json = spec.output.parent / "run.json"
    run_json.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
    return RunResult(plan, result.returncode, result.stdout, result.stderr, duration, checksum, run_json)


def run_end_params(events_path: Path) -> dict:
    if not events_path.exists():
        return {}
    for line in reversed(events_path.read_text(encoding="utf-8").splitlines()):
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if data.get("event") == "run_end":
            return data.get("params", {})
    return {}
