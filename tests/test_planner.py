from pathlib import Path

import pytest

from bhlab.capabilities import Capabilities
from bhlab.config import Config
from bhlab.planner import PlanError, RunSpec, resolve


def caps(**overrides) -> Capabilities:
    values = {
        "mpi": True, "charm": True, "charm_launcher": "charmrun",
        "cuda": True, "openmp": True,
    }
    values.update(overrides)
    return Capabilities(**values)


def spec(tmp_path: Path, **overrides) -> RunSpec:
    values = {
        "app": "kmer",
        "input": tmp_path / "reads.fq",
        "output": tmp_path / "run" / "counts.tsv",
    }
    values.update(overrides)
    return RunSpec(**values)


def test_auto_prefers_mpi(tmp_path: Path) -> None:
    plan = resolve(spec(tmp_path), Config(root=tmp_path), caps())
    assert plan.comm == "mpi"
    assert plan.launcher == "mpirun"
    assert plan.device == "gpu"
    assert plan.layout == "soa2"
    assert plan.argv[0] == "mpirun"
    assert "--verify-shuffle" not in plan.argv


def test_auto_respects_comm_order(tmp_path: Path) -> None:
    config = Config(root=tmp_path, comm_order=["charm", "mpi", "local"])
    plan = resolve(spec(tmp_path), config, caps())
    assert plan.comm == "charm"
    assert plan.argv[0] == "charmrun"


def test_explicit_unavailable_backend_fails(tmp_path: Path) -> None:
    with pytest.raises(PlanError):
        resolve(spec(tmp_path, comm="charm"), Config(root=tmp_path), caps(charm=False))


def test_charm_prterun_launcher(tmp_path: Path) -> None:
    plan = resolve(
        spec(tmp_path, comm="charm"), Config(root=tmp_path), caps(charm_launcher="prterun"),
    )
    assert plan.argv[:3] == ["prterun", "-n", "1"]


def test_gpu_without_cuda_fails(tmp_path: Path) -> None:
    with pytest.raises(PlanError):
        resolve(spec(tmp_path, device="gpu"), Config(root=tmp_path), caps(cuda=False))


def test_explicit_layout_is_kept(tmp_path: Path) -> None:
    plan = resolve(spec(tmp_path, layout="aos8", device="gpu"), Config(root=tmp_path), caps())
    assert plan.layout == "aos8"


def test_minimizer_is_local_only(tmp_path: Path) -> None:
    with pytest.raises(PlanError):
        resolve(spec(tmp_path, app="minimizer", comm="mpi"), Config(root=tmp_path), caps())
    plan = resolve(spec(tmp_path, app="minimizer", comm="auto"), Config(root=tmp_path), caps())
    assert plan.comm == "local"


def test_dry_run_command_contains_paths(tmp_path: Path) -> None:
    plan = resolve(spec(tmp_path), Config(root=tmp_path), caps())
    assert "mpirun" in plan.command
    assert str(tmp_path / "reads.fq") in plan.command
