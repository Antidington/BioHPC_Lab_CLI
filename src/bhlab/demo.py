from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from bhlab.bench import bench
from bhlab.build import build
from bhlab.capabilities import detect
from bhlab.codegen import generate
from bhlab.config import Config
from bhlab.logs import baseline
from bhlab.logs.normalize import normalize
from bhlab.logs.rules import load_rules
from bhlab.logs.store import Store
from bhlab.logs.watch import Watcher
from bhlab.planner import RunSpec
from bhlab.runner import run


class DemoError(RuntimeError):
    pass


def _run_or_fail(spec: RunSpec, config: Config) -> object:
    result = run(spec, config)
    if result.returncode != 0:
        raise DemoError(f"run failed: {result.plan.command}\n{result.stderr}")
    return result


def acceptance(config: Config, full: bool = False) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    evidence = config.evidence / stamp
    evidence.mkdir(parents=True, exist_ok=True)
    if not (config.build / "bin" / "bhlab-kmer").exists():
        build(config, "local-clang")
    build(config, "local-clang")

    tiny = config.root / "fixtures" / "reads" / "tiny.fq"
    kmer_dir = evidence / "runs" / "kmer"
    minimizer_dir = evidence / "runs" / "minimizer"
    kmer = _run_or_fail(RunSpec(
        app="kmer", input=tiny, output=kmer_dir / "counts.tsv",
        comm="local", device="cpu", layout="aos8", k=15, job_id="demo-kmer",
    ), config)
    minimizer = _run_or_fail(RunSpec(
        app="minimizer", input=tiny, output=minimizer_dir / "minimizer.tsv",
        comm="local", device="cpu", layout="aos8", k=15, window=8, job_id="demo-minimizer",
    ), config)

    caps = detect()
    backend_checks: dict[str, object] = {}
    generated: list[Path] = []
    generated.append(generate(config, config.root / "pipelines" / "kmer_qc.bhl", "local",
                              config.build / "gen" / "kmer_qc_local.cpp")[0])
    for comm in ("mpi", "charm"):
        try:
            generated.extend(generate(config, config.root / "pipelines" / "kmer_qc.bhl", comm))
        except Exception as error:
            if full:
                raise DemoError(f"code generation failed for {comm}: {error}") from error

    if full and caps.mpi:
        try:
            build(config, "mpi-clang")
        except Exception as error:
            backend_checks["mpi_build"] = f"unavailable: {error}"
    if full and caps.charm:
        try:
            build(config, "charm-clang", with_charm=True)
        except Exception as error:
            backend_checks["charm_build"] = f"unavailable: {error}"

    matrix = (
        "comm=local,mpi,charm;device=cpu,gpu;layout=aos8,soa2"
        if full else "comm=local;device=cpu;layout=aos8,soa2"
    )
    bench_rows = bench(
        config, tiny, evidence / "bench", _matrix(matrix),
        repeat=3 if full else 1, k=15, allow_missing=full,
    )

    build(config, "local-clang")
    generated_bin = config.build / "bin" / "kmer_qc"
    if not generated_bin.exists():
        raise DemoError(f"generated binary was not built: {generated_bin}")
    generated_out = evidence / "generated" / "counts.tsv"
    generated_result = run(RunSpec(
        app="kmer", input=tiny, output=generated_out,
        comm="local", device="cpu", layout="aos8", k=15, job_id="demo-codegen",
        binary=generated_bin,
    ), config)
    if generated_result.returncode != 0:
        raise DemoError("generated local driver failed")
    if generated_result.checksum != kmer.checksum:
        raise DemoError("generated driver checksum differs from the hand-written app")

    if full and caps.mpi and "mpi_build" not in backend_checks:
        try:
            mpi_bin = config.build / "bin" / "kmer_qc_mpi"
            if mpi_bin.exists():
                result = _run_or_fail(RunSpec(
                    app="kmer", input=tiny, output=evidence / "generated" / "mpi.tsv",
                    comm="mpi", nodes=2, k=15, layout="aos8",
                    job_id="demo-codegen-mpi", binary=mpi_bin,
                ), config)
                backend_checks["mpi"] = result.checksum == kmer.checksum
                if not backend_checks["mpi"]:
                    raise DemoError("generated MPI driver checksum differs")
        except DemoError:
            raise
        except Exception as error:
            backend_checks["mpi"] = f"unavailable: {error}"
    if full and caps.charm and "charm_build" not in backend_checks:
        try:
            charm_bin = config.build / "bin" / "kmer_qc_charm"
            if charm_bin.exists():
                result = _run_or_fail(RunSpec(
                    app="kmer", input=tiny, output=evidence / "generated" / "charm.tsv",
                    comm="charm", nodes=2, k=15, layout="aos8",
                    job_id="demo-codegen-charm", binary=charm_bin,
                ), config)
                backend_checks["charm"] = result.checksum == kmer.checksum
                if not backend_checks["charm"]:
                    raise DemoError("generated Charm++ driver checksum differs")
        except DemoError:
            raise
        except Exception as error:
            backend_checks["charm"] = f"unavailable: {error}"

    normal_root = config.runs / "demo-normal"
    if normal_root.exists():
        shutil.rmtree(normal_root)
    for index in range(10):
        _run_or_fail(RunSpec(
            app="kmer", input=tiny, output=normal_root / f"run-{index:02d}" / "counts.tsv",
            comm="local", device="cpu", layout="aos8", k=15, job_id=f"normal-{index:02d}",
        ), config)
    history = baseline.load_history(normal_root)
    model = baseline.build(history, config.min_samples)
    baseline_path = evidence / "baselines.json"
    baseline.write(model, baseline_path)
    model_entries = list(model.get("models", {}).values())
    if not model_entries or all(entry.get("insufficient") for entry in model_entries):
        raise DemoError("baseline has too few normal samples")

    db = evidence / "events.db"
    if db.exists():
        db.unlink()
    source_counts = normalize(
        [
            f"app:{config.root / 'fixtures' / 'logs' / 'fault.jsonl'}",
            f"slurm:{config.root / 'fixtures' / 'logs' / 'slurm_job.out'}",
            f"syslog:{config.root / 'fixtures' / 'logs' / 'syslog.txt'}",
        ],
        db,
    )
    if len([key for key, value in source_counts.items() if value > 0]) < 3:
        raise DemoError(f"expected three log sources, got {source_counts}")

    rules = load_rules(config.root / "rules" / "default.toml")
    store = Store(db)
    watcher = Watcher(
        store, rules, model, window=config.window,
        dedupe_seconds=config.dedupe_seconds, webhook=config.webhook,
    )
    alerts = watcher.replay(config.root / "fixtures" / "logs" / "fault.jsonl")
    stats = store.stats()
    store.close()
    if not alerts:
        raise DemoError("fault replay produced no alert")

    checksums = evidence / "checksums.txt"
    checksums.write_text(
        f"{kmer.checksum}  kmer\n"
        f"{generated_result.checksum}  generated\n"
        f"{generated_result.checksum == kmer.checksum}  checksum_match\n",
        encoding="utf-8",
    )
    summary = evidence / "SUMMARY.md"
    summary.write_text(
        "# BioHPC Lab acceptance evidence\n\n"
        f"- generated: {stamp}\n"
        f"- kmer checksum: `{kmer.checksum}`\n"
        f"- generated driver checksum: `{generated_result.checksum}`\n"
        f"- checksum match: {generated_result.checksum == kmer.checksum}\n"
        f"- minimizer output: `{minimizer.plan.spec.output}`\n"
        f"- bench rows: {len(bench_rows)}\n"
        f"- baseline samples: {model_entries[0].get('n') if model_entries else 0}\n"
        f"- log sources: {source_counts}\n"
        f"- backend checks: {backend_checks}\n"
        f"- alerts: {[alert['id'] for alert in alerts]}\n"
        f"- event stats: {json.dumps(stats, sort_keys=True)}\n"
        f"- generated sources: {[str(path) for path in generated]}\n",
        encoding="utf-8",
    )
    print(f"evidence written to {evidence}")
    print(f"checksum match: {generated_result.checksum == kmer.checksum}")
    print(f"alerts: {[(alert['id'], alert['rule_id']) for alert in alerts]}")
    return evidence


def _matrix(value: str) -> dict[str, list[str]]:
    from bhlab.bench import parse_matrix

    return parse_matrix(value)
