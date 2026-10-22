from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10
    import tomli as tomllib


DEFAULT_CONFIG = """# BioHPC Lab configuration.
[comm]
order = ["mpi", "charm", "local"]

[device]
order = ["gpu", "cpu"]

[layout]
map = { gpu = "soa2", cpu = "aos8" }

[paths]
build = "build"
runs = "runs"
db = "var/events.db"
evidence = "evidence"

[bench]
repeat = 3
platform = "local-clang"

[anomaly]
min_samples = 8
window = 50
dedupe_seconds = 300
webhook = ""
"""


@dataclass
class Config:
    root: Path
    comm_order: list[str] = field(default_factory=lambda: ["mpi", "charm", "local"])
    device_order: list[str] = field(default_factory=lambda: ["gpu", "cpu"])
    layout_map: dict[str, str] = field(default_factory=lambda: {"gpu": "soa2", "cpu": "aos8"})
    build_dir: str = "build"
    runs_dir: str = "runs"
    db_path: str = "var/events.db"
    evidence_dir: str = "evidence"
    repeat: int = 3
    platform: str = "local-clang"
    min_samples: int = 8
    window: int = 50
    dedupe_seconds: int = 300
    webhook: str = ""

    @classmethod
    def load(cls, root: Path | None = None) -> Config:
        base = Path(root or os.environ.get("BHLAB_ROOT") or Path.cwd()).resolve()
        path = base / "bhlab.toml"
        if not path.exists():
            return cls(root=base)
        with path.open("rb") as handle:
            data = tomllib.load(handle)
        return cls(
            root=base,
            comm_order=list(data.get("comm", {}).get("order", ["mpi", "charm", "local"])),
            device_order=list(data.get("device", {}).get("order", ["gpu", "cpu"])),
            layout_map=dict(data.get("layout", {}).get("map", {"gpu": "soa2", "cpu": "aos8"})),
            build_dir=data.get("paths", {}).get("build", "build"),
            runs_dir=data.get("paths", {}).get("runs", "runs"),
            db_path=data.get("paths", {}).get("db", "var/events.db"),
            evidence_dir=data.get("paths", {}).get("evidence", "evidence"),
            repeat=int(data.get("bench", {}).get("repeat", 3)),
            platform=data.get("bench", {}).get("platform", "local-clang"),
            min_samples=int(data.get("anomaly", {}).get("min_samples", 8)),
            window=int(data.get("anomaly", {}).get("window", 50)),
            dedupe_seconds=int(data.get("anomaly", {}).get("dedupe_seconds", 300)),
            webhook=data.get("anomaly", {}).get("webhook", ""),
        )

    def path(self, value: str) -> Path:
        candidate = Path(value)
        return candidate if candidate.is_absolute() else self.root / candidate

    @property
    def build(self) -> Path:
        return self.path(self.build_dir)

    @property
    def runs(self) -> Path:
        return self.path(self.runs_dir)

    @property
    def db(self) -> Path:
        return self.path(self.db_path)

    @property
    def evidence(self) -> Path:
        return self.path(self.evidence_dir)

    def write(self) -> Path:
        path = self.root / "bhlab.toml"
        path.write_text(DEFAULT_CONFIG, encoding="utf-8")
        return path
