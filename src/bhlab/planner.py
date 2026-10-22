from __future__ import annotations

import shlex
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from bhlab.capabilities import Capabilities
from bhlab.config import Config


class PlanError(RuntimeError):
    pass


@dataclass
class RunSpec:
    app: str
    input: Path
    output: Path
    comm: str = "auto"
    device: str = "auto"
    layout: str = "auto"
    nodes: int = 1
    ranks_per_node: int = 1
    threads: int = 1
    k: int = 21
    window: int = 10
    max_reads: int = 0
    job_id: str = ""
    events: Path | None = None
    verify_shuffle: bool = False
    hostfile: str = ""
    emit_slurm: Path | None = None
    binary: Path | None = None


@dataclass
class LaunchPlan:
    spec: RunSpec
    comm: str
    device: str
    layout: str
    launcher: str
    argv: list[str]
    reason: str
    binary: Path
    env: dict[str, str] = field(default_factory=dict)

    @property
    def command(self) -> str:
        return " ".join(shlex.quote(part) for part in self.argv)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["spec"] = asdict(self.spec)
        data["spec"]["input"] = str(self.spec.input)
        data["spec"]["output"] = str(self.spec.output)
        data["spec"]["events"] = str(self.spec.events) if self.spec.events else None
        data["spec"]["emit_slurm"] = str(self.spec.emit_slurm) if self.spec.emit_slurm else None
        data["spec"]["binary"] = str(self.spec.binary) if self.spec.binary else None
        data["binary"] = str(self.binary)
        return data

    def slurm_script(self, root: Path | None = None) -> str:
        base = Path(root) if root is not None else Path.cwd()
        lines = [
            "#!/usr/bin/env bash",
            f"#SBATCH --job-name=bhlab-{self.spec.app}",
            f"#SBATCH --nodes={self.spec.nodes}",
            f"#SBATCH --ntasks={self.spec.nodes * self.spec.ranks_per_node}",
            "#SBATCH --time=00:30:00",
            "set -euo pipefail",
            f"cd {shlex.quote(str(base))}",
            self.command,
        ]
        return "\n".join(lines) + "\n"


def _choose_comm(spec: RunSpec, config: Config, caps: Capabilities) -> tuple[str, str]:
    available = set(caps.available_comm())
    if spec.comm != "auto":
        if spec.comm not in available:
            raise PlanError(
                f"comm '{spec.comm}' is unavailable; detected: {', '.join(sorted(available))}. "
                "Run 'bhlab doctor' for details."
            )
        return spec.comm, f"explicit --comm {spec.comm}"
    for candidate in config.comm_order:
        if candidate in available:
            return candidate, f"auto selected '{candidate}' from comm_order {config.comm_order}"
    raise PlanError("no communication backend is available; install MPI or use --comm local")


def _choose_device(spec: RunSpec, config: Config, caps: Capabilities) -> tuple[str, str]:
    if spec.device != "auto":
        if spec.device == "gpu" and not caps.cuda:
            raise PlanError("device 'gpu' requested but CUDA was not detected")
        if spec.device not in {"cpu", "gpu"}:
            raise PlanError("device must be auto, cpu, or gpu")
        return spec.device, f"explicit --device {spec.device}"
    for candidate in config.device_order:
        if candidate == "gpu" and not caps.cuda:
            continue
        if candidate in {"cpu", "gpu"}:
            return candidate, f"auto selected '{candidate}' from device_order {config.device_order}"
    return "cpu", "fallback to cpu"


def _choose_layout(spec: RunSpec, config: Config, device: str) -> tuple[str, str]:
    if spec.layout != "auto":
        if spec.layout not in {"aos8", "soa2"}:
            raise PlanError("layout must be auto, aos8, or soa2")
        return spec.layout, f"explicit --layout {spec.layout}"
    layout = config.layout_map.get(device, "aos8")
    return layout, f"auto mapped device '{device}' to layout '{layout}'"


def resolve(spec: RunSpec, config: Config, caps: Capabilities) -> LaunchPlan:
    spec.input = Path(spec.input)
    spec.output = Path(spec.output)
    if spec.app not in {"kmer", "minimizer"}:
        raise PlanError("app must be kmer or minimizer")
    if spec.k < 1 or spec.k > 31:
        raise PlanError("k must be between 1 and 31")
    if spec.nodes < 1 or spec.ranks_per_node < 1:
        raise PlanError("nodes and ranks per node must be positive")
    if spec.app == "minimizer" and spec.comm in {"mpi", "charm"}:
        raise PlanError("the minimizer app currently runs only with --comm local")
    if spec.comm == "auto" and spec.app == "minimizer":
        spec.comm = "local"

    comm, comm_reason = _choose_comm(spec, config, caps)
    device, device_reason = _choose_device(spec, config, caps)
    layout, layout_reason = _choose_layout(spec, config, device)

    suffix = "" if comm == "local" else f"-{comm}"
    binary = Path(spec.binary) if spec.binary else config.build / "bin" / f"bhlab-{spec.app}{suffix}"
    np = spec.nodes * spec.ranks_per_node
    if not spec.job_id:
        stem = spec.output.parent.name if spec.output.parent.name not in {"", "."} else ""
        spec.job_id = stem or f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    if spec.events is None:
        spec.events = spec.output.parent / "events.jsonl"

    native_argv = [
        str(binary),
        "--app", spec.app,
        "--input", str(spec.input),
        "--output", str(spec.output),
        "--events", str(spec.events),
        "--job-id", spec.job_id,
        "--layout", layout,
        "--device", device,
        "--threads", str(spec.threads),
        "--k", str(spec.k),
        "--window", str(spec.window),
    ]
    if spec.max_reads:
        native_argv += ["--max-reads", str(spec.max_reads)]
    if spec.verify_shuffle:
        native_argv.append("--verify-shuffle")

    if comm == "mpi":
        argv = ["mpirun", "-np", str(np)]
        if spec.hostfile:
            argv += ["--hostfile", spec.hostfile]
        argv += native_argv
        launcher = "mpirun"
    elif comm == "charm":
        if caps.charm_launcher == "charmrun":
            argv = ["charmrun", "+p", str(np)] + native_argv
            launcher = "charmrun"
        elif caps.charm_launcher == "prterun":
            argv = ["prterun", "-n", str(np)] + native_argv
            launcher = "prterun"
        else:
            raise PlanError("Charm++ is installed but no launcher (charmrun or prterun) was found")
    else:
        argv = native_argv
        launcher = "direct"

    reason = f"{comm_reason}; {device_reason}; {layout_reason}"
    return LaunchPlan(
        spec=spec,
        comm=comm,
        device=device,
        layout=layout,
        launcher=launcher,
        argv=argv,
        reason=reason,
        binary=binary,
        env={"BHLAB_JOB_ID": spec.job_id, "OMP_NUM_THREADS": str(spec.threads)},
    )
