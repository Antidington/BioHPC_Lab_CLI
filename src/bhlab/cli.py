from __future__ import annotations

import json
from pathlib import Path

import typer

from bhlab import __version__
from bhlab.bench import BenchError, bench, parse_matrix
from bhlab.build import BuildError, build
from bhlab.capabilities import detect
from bhlab.codegen import CodegenError, generate
from bhlab.config import Config
from bhlab.demo import DemoError, acceptance
from bhlab.logs import baseline
from bhlab.logs.keywords import extract
from bhlab.logs.normalize import normalize
from bhlab.logs.rules import load_rules
from bhlab.logs.schema import LogEvent, SchemaError
from bhlab.logs.store import Store
from bhlab.logs.watch import Watcher
from bhlab.planner import PlanError, RunSpec
from bhlab.runner import RunnerError, run

app = typer.Typer(no_args_is_help=True, help="BioHPC Lab command line tool.")
deps_app = typer.Typer(help="Inspect external libraries.")
log_app = typer.Typer(help="Normalize, query, and inspect logs.")
baseline_app = typer.Typer(help="Build and inspect normal-behavior baselines.")
alert_app = typer.Typer(help="Inspect alerts.")
demo_app = typer.Typer(help="Run the acceptance story.")
app.add_typer(deps_app, name="deps")
app.add_typer(log_app, name="log")
app.add_typer(baseline_app, name="baseline")
app.add_typer(alert_app, name="alert")
app.add_typer(demo_app, name="demo")


@app.callback()
def main(ctx: typer.Context, root: Path = typer.Option(Path.cwd(), "--root", help="Project root.")) -> None:
    ctx.obj = Config.load(root)


def _config(ctx: typer.Context) -> Config:
    return ctx.obj


@app.command()
def version() -> None:
    """Print the tool version."""
    typer.echo(__version__)


@app.command()
def init(ctx: typer.Context, force: bool = typer.Option(False, "--force")) -> None:
    """Write bhlab.toml and create the working directories."""
    config = _config(ctx)
    target = config.root / "bhlab.toml"
    if target.exists() and not force:
        typer.echo(f"{target} already exists; use --force to replace it")
        raise typer.Exit(1)
    config.write()
    for directory in (config.build, config.runs, config.db.parent, config.evidence):
        directory.mkdir(parents=True, exist_ok=True)
    typer.echo(f"initialized {config.root}")


@app.command()
def doctor(ctx: typer.Context, as_json: bool = typer.Option(False, "--json")) -> None:
    """Report compilers, runners, devices, and libraries."""
    caps = detect()
    if as_json:
        typer.echo(json.dumps(caps.to_dict(), indent=2, sort_keys=True))
        return
    typer.echo(f"mpi:    {'yes' if caps.mpi else 'no'}")
    if caps.charm:
        launcher = caps.charm_launcher or "no launcher"
        typer.echo(f"charm:  yes ({launcher})")
    else:
        typer.echo("charm:  no")
    typer.echo(f"cuda:   {'yes' if caps.cuda else 'no'}")
    typer.echo(f"openmp: {'yes' if caps.openmp else 'no'}")
    typer.echo(f"slurm:  {'yes' if caps.slurm else 'no'}")
    for name, path in caps.compilers.items():
        if path:
            typer.echo(f"{name:8} {path}")
    typer.echo("libraries:")
    for name, library in caps.libraries.items():
        mark = "ok" if library.found else "missing"
        typer.echo(f"  {name:10} {mark:7} {library.version:10} {library.detail}")


@deps_app.command("probe")
def deps_probe(as_json: bool = typer.Option(False, "--json")) -> None:
    """Probe the five configured external libraries."""
    caps = detect()
    if as_json:
        typer.echo(json.dumps({key: value.__dict__ for key, value in caps.libraries.items()},
                              indent=2, sort_keys=True))
        return
    for name, library in caps.libraries.items():
        mark = "ok" if library.found else "missing"
        typer.echo(f"{name:10} {mark:7} {library.version:10} {library.cflags} {library.libs}")


def build_cmd(
    ctx: typer.Context,
    platform: str = typer.Option(None, "--platform"),
    emit_only: bool = typer.Option(False, "--emit-only", help="Write Makefile and config.mk only."),
    jobs: int = typer.Option(4, "--jobs"),
    with_charm: bool = typer.Option(False, "--with-charm"),
) -> None:
    """Generate a platform Makefile and build the native binaries."""
    config = _config(ctx)
    try:
        result = build(config, platform, emit_only, jobs, with_charm)
    except (BuildError, FileNotFoundError) as error:
        typer.echo(str(error))
        raise typer.Exit(1)
    typer.echo(f"platform: {result.platform}")
    typer.echo(f"makefile: {result.makefile}")
    typer.echo(f"config:   {result.config_mk}")
    if result.ran_make:
        typer.echo("build: ok")
    else:
        typer.echo("build: emitted only")


app.command("build")(build_cmd)


@app.command()
def codegen(
    ctx: typer.Context,
    pipeline: Path = typer.Argument(..., exists=True),
    comm: str = typer.Option("local", "--comm"),
    out: Path = typer.Option(None, "--out"),
) -> None:
    """Generate a C++ driver from a pipeline file."""
    config = _config(ctx)
    try:
        paths = generate(config, pipeline, comm, out)
    except CodegenError as error:
        typer.echo(str(error))
        raise typer.Exit(1)
    for path in paths:
        typer.echo(path)


def run_cmd(
    ctx: typer.Context,
    input_path: Path = typer.Option(..., "--input", exists=True),
    output: Path = typer.Option(..., "--output"),
    app_name: str = typer.Option("kmer", "--app"),
    comm: str = typer.Option("auto", "--comm"),
    device: str = typer.Option("auto", "--device"),
    layout: str = typer.Option("auto", "--layout"),
    nodes: int = typer.Option(1, "--nodes"),
    ranks_per_node: int = typer.Option(1, "--ranks-per-node"),
    threads: int = typer.Option(1, "--threads"),
    k: int = typer.Option(21, "--k"),
    window: int = typer.Option(10, "--window"),
    max_reads: int = typer.Option(0, "--max-reads"),
    job_id: str = typer.Option("", "--job-id"),
    verify_shuffle: bool = typer.Option(False, "--verify-shuffle"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    emit_slurm: Path = typer.Option(None, "--emit-slurm"),
) -> None:
    """Run one native task or print the resolved launch plan."""
    config = _config(ctx)
    spec = RunSpec(
        app=app_name, input=input_path, output=output, comm=comm, device=device,
        layout=layout, nodes=nodes, ranks_per_node=ranks_per_node, threads=threads,
        k=k, window=window, max_reads=max_reads, job_id=job_id,
        verify_shuffle=verify_shuffle, emit_slurm=emit_slurm,
    )
    if dry_run:
        from bhlab.planner import resolve

        plan = resolve(spec, config, detect())
        typer.echo(f"reason: {plan.reason}")
        typer.echo(plan.command)
        return
    try:
        result = run(spec, config)
    except (PlanError, RunnerError) as error:
        typer.echo(str(error))
        raise typer.Exit(1)
    if result.stdout:
        typer.echo(result.stdout.rstrip("\n"))
    if result.stderr:
        typer.echo(result.stderr.rstrip("\n"), err=True)
    typer.echo(f"exit: {result.returncode}")
    if result.checksum:
        typer.echo(f"sha256: {result.checksum}")
    if result.returncode != 0:
        raise typer.Exit(result.returncode)


app.command("run")(run_cmd)


def bench_cmd(
    ctx: typer.Context,
    input_path: Path = typer.Option(..., "--input", exists=True),
    out: Path = typer.Option(Path("evidence/bench"), "--out"),
    matrix: str = typer.Option("comm=local;device=cpu;layout=aos8,soa2", "--matrix"),
    repeat: int = typer.Option(3, "--repeat"),
    k: int = typer.Option(21, "--k"),
    app_name: str = typer.Option("kmer", "--app"),
    allow_missing: bool = typer.Option(False, "--allow-missing"),
) -> None:
    """Run a benchmark matrix and write CSV plus a manifest."""
    config = _config(ctx)
    try:
        bench(
            config, input_path, out, parse_matrix(matrix), repeat=repeat, k=k,
            app=app_name, allow_missing=allow_missing,
        )
    except (BenchError, PlanError, RunnerError) as error:
        typer.echo(str(error))
        raise typer.Exit(1)


app.command("bench")(bench_cmd)


@log_app.command("normalize")
def log_normalize(
    ctx: typer.Context,
    source: list[str] = typer.Option(..., "--source", help="app:PATH, slurm:PATH, or syslog:PATH"),
    db: Path = typer.Option(None, "--db"),
) -> None:
    """Normalize one or more log sources into SQLite."""
    config = _config(ctx)
    try:
        counts = normalize(source, db or config.db)
    except FileNotFoundError as error:
        typer.echo(str(error))
        raise typer.Exit(1)
    typer.echo(json.dumps(counts, sort_keys=True))


@log_app.command("query")
def log_query(
    ctx: typer.Context,
    db: Path = typer.Option(None, "--db"),
    job: str = typer.Option("", "--job"),
    source: str = typer.Option("", "--source"),
    event: str = typer.Option("", "--event"),
    level: str = typer.Option("", "--level"),
    grep: str = typer.Option("", "--grep"),
    since: str = typer.Option("", "--since"),
    until: str = typer.Option("", "--until"),
    sort: str = typer.Option("ts", "--sort"),
    limit: int = typer.Option(100, "--limit"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Sort, filter, and print normalized events."""
    config = _config(ctx)
    store = Store(db or config.db)
    try:
        events = store.query(job, source, event, level, grep, since, until, sort, limit)
    finally:
        store.close()
    if as_json:
        for item in events:
            typer.echo(item.to_json())
        return
    typer.echo(f"{'ts':21} {'source':8} {'job':14} {'event':14} {'level':8} message")
    for item in events:
        typer.echo(f"{item.ts:21} {item.source:8} {item.job_id:14} {item.event:14} {item.level:8} {item.message}")


@log_app.command("keywords")
def log_keywords(
    ctx: typer.Context,
    db: Path = typer.Option(None, "--db"),
    job: str = typer.Option("", "--job"),
    top: int = typer.Option(20, "--top"),
) -> None:
    """Extract terms that stand out in a job against the rest of the corpus."""
    config = _config(ctx)
    store = Store(db or config.db)
    try:
        rows = extract(store, job, top)
    finally:
        store.close()
    for row in rows:
        mark = "!" if row["anomaly"] else " "
        typer.echo(f"{mark} {row['token']:24} count={row['count']:<5} score={row['score']}")


@log_app.command("stats")
def log_stats(ctx: typer.Context, db: Path = typer.Option(None, "--db")) -> None:
    """Show event counts by source and level."""
    config = _config(ctx)
    store = Store(db or config.db)
    try:
        typer.echo(json.dumps(store.stats(), indent=2, sort_keys=True))
    finally:
        store.close()


@log_app.command("export")
def log_export(
    ctx: typer.Context,
    out: Path = typer.Option(..., "--out"),
    db: Path = typer.Option(None, "--db"),
    job: str = typer.Option("", "--job"),
    source: str = typer.Option("", "--source"),
    grep: str = typer.Option("", "--grep"),
    limit: int = typer.Option(100000, "--limit"),
) -> None:
    """Export normalized events as JSONL."""
    config = _config(ctx)
    store = Store(db or config.db)
    try:
        events = store.query(job=job, source=source, grep=grep, limit=limit)
        count = store.export_jsonl(out, events)
    finally:
        store.close()
    typer.echo(f"exported {count} events to {out}")


@log_app.command("validate")
def log_validate(path: Path = typer.Argument(..., exists=True)) -> None:
    """Validate a JSONL file against the event schema."""
    errors = 0
    count = 0
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            LogEvent.from_json(line)
            count += 1
        except SchemaError as error:
            errors += 1
            typer.echo(f"{path}:{number}: {error}")
    typer.echo(f"valid={count} errors={errors}")
    if errors:
        raise typer.Exit(1)


@baseline_app.command("build")
def baseline_build(
    ctx: typer.Context,
    history: Path = typer.Option(None, "--history", help="Directory of JSONL event files."),
    out: Path = typer.Option(None, "--out"),
    db: Path = typer.Option(None, "--db"),
    min_samples: int = typer.Option(8, "--min-samples"),
) -> None:
    """Build robust per-signature statistics from successful historical jobs."""
    config = _config(ctx)
    if history:
        events = baseline.load_history(history)
    else:
        store = Store(db or config.db)
        try:
            events = store.query(limit=1000000)
        finally:
            store.close()
    model = baseline.build(events, min_samples)
    target = out or (config.root / "baselines" / "baselines.json")
    baseline.write(model, target)
    typer.echo(f"wrote {target} with {len(model['models'])} signature(s)")
    for key, entry in sorted(model["models"].items()):
        typer.echo(f"{key} n={entry['n']} insufficient={entry['insufficient']}")


@baseline_app.command("evaluate")
def baseline_evaluate(
    ctx: typer.Context,
    baseline_path: Path = typer.Option(..., "--baseline", exists=True),
    history: Path = typer.Option(..., "--history"),
) -> None:
    """Evaluate historical jobs against a baseline."""
    model = baseline.load(baseline_path)
    for summary in baseline.collect(baseline.load_history(history)):
        findings = baseline.evaluate(model, summary)
        typer.echo(f"{summary.job_id}: {findings}")


@app.command()
def watch(
    ctx: typer.Context,
    rules_path: Path = typer.Option(None, "--config"),
    db: Path = typer.Option(None, "--db"),
    baseline_path: Path = typer.Option(None, "--baseline"),
    replay: Path = typer.Option(None, "--replay"),
    source: list[str] = typer.Option([], "--source", help="Live source, such as app:runs/job/events.jsonl"),
    once: bool = typer.Option(False, "--once"),
    interval: float = typer.Option(1.0, "--interval"),
    delay: float = typer.Option(0.0, "--delay"),
) -> None:
    """Detect anomalies in replayed or live logs and send alerts."""
    config = _config(ctx)
    rules_file = rules_path or (config.root / "rules" / "default.toml")
    if not rules_file.exists():
        typer.echo(f"rules file not found: {rules_file}")
        raise typer.Exit(1)
    model = baseline.load(baseline_path) if baseline_path else {"models": {}, "min_samples": 8}
    store = Store(db or config.db)
    watcher = Watcher(
        store, load_rules(rules_file), model, window=config.window,
        dedupe_seconds=config.dedupe_seconds, webhook=config.webhook,
    )
    try:
        if replay:
            watcher.replay(replay, delay=delay)
        elif source:
            watcher.follow(source, interval=interval, max_iterations=1 if once else None)
        else:
            typer.echo("provide --replay FILE or at least one --source")
            raise typer.Exit(1)
    finally:
        store.close()
    typer.echo(f"alerts: {len(watcher.alerts)}")


@alert_app.command("list")
def alert_list(ctx: typer.Context, db: Path = typer.Option(None, "--db"),
               limit: int = typer.Option(50, "--limit")) -> None:
    """List recent alerts."""
    config = _config(ctx)
    store = Store(db or config.db)
    try:
        for alert in store.list_alerts(limit):
            typer.echo(
                f"{alert['id']:4} {alert['ts']} [{alert['severity']}] "
                f"job={alert['job_id']} rule={alert['rule_id']} {alert['message']}"
            )
    finally:
        store.close()


@alert_app.command("show")
def alert_show(ctx: typer.Context, alert_id: int = typer.Argument(...),
               db: Path = typer.Option(None, "--db")) -> None:
    """Show one alert and the events that preceded it."""
    config = _config(ctx)
    store = Store(db or config.db)
    try:
        alert = store.get_alert(alert_id)
    finally:
        store.close()
    if alert is None:
        typer.echo(f"alert {alert_id} not found")
        raise typer.Exit(1)
    typer.echo(f"alert {alert['id']} {alert['ts']} [{alert['severity']}] "
               f"job={alert['job_id']} rule={alert['rule_id']}")
    typer.echo(alert["message"])
    typer.echo("preceding events:")
    for event in alert["evidence"]:
        typer.echo(f"  {event['ts']} {event['source']:7} {event['event']:14} {event.get('message', '')}")


@demo_app.command("acceptance")
def demo_acceptance(ctx: typer.Context, full: bool = typer.Option(False, "--full")) -> None:
    """Run the end-to-end acceptance story and write evidence."""
    config = _config(ctx)
    try:
        acceptance(config, full=full)
    except DemoError as error:
        typer.echo(str(error))
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
