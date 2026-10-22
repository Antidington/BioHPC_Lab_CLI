# Architecture Overview

- Status: Accepted
- Owner: BioHPC Lab
- Scaffold created: 2026-10-22
- Last verified: 2026-10-22

## System context

`bhlab` is a standalone lab bench. It reads sequencing reads, builds native
binaries, runs a kernel through a chosen communication and device backend, and
normalizes the events from those runs. The same event stream feeds the anomaly
pipeline. The tool never submits Slurm jobs and never calls the production
platform.

```
user
  |
  v
bhlab CLI (Python, Typer)
  |-- doctor / deps ------> Capabilities
  |-- build --------------> config.<platform>.mk + Makefile.<platform>
  |-- codegen ------------> build/gen/*.cpp and *.ci
  |-- run / bench --------> LaunchPlan -> mpirun / charmrun / direct
  |-- log / watch --------> LogEvent -> SQLite -> Baseline -> Rule -> Alert
  |
  v
native/ C++17
  core: SeqBatch, KmerTable, k-mer, minimizer
  layout: aos8, soa2
  device: cpu_omp, cuda
  comm: mpi_driver, charm_driver
```

The product loop is `doctor -> build -> run -> bench -> log -> baseline ->
watch`. Each step produces a file that the next step can consume and a reviewer
can inspect.

## Components and boundaries

- `src/bhlab/cli.py` owns the command surface. It validates input and prints
  results. It does not decide backend selection.
- `src/bhlab/planner.py` owns the `RunSpec` to `LaunchPlan` decision. The comm
  order, device order, and layout map come from `bhlab.toml`. An explicit
  backend that is unavailable raises `PlanError`. An auto choice prints its
  reason.
- `src/bhlab/capabilities.py` probes compilers, MPI, Charm++, CUDA, Slurm, and
  the five libraries. A failed probe is data, not an exception.
- `src/bhlab/deps.py` and `src/bhlab/build.py` turn a platform profile and the
  capability report into `build/config.<platform>.mk` and
  `build/Makefile.<platform>`. Each platform has its own config file, so
  generating a GPU Makefile does not break a CPU build.
- `src/bhlab/codegen.py` parses the line-based pipeline DSL and renders C++
  drivers with Jinja2. Templates live in `src/bhlab/codegen_templates/`.
- `native/include/bhlab/` holds the data types and public interfaces.
- `native/src/` holds the core algorithms, the local CPU backend, the optional
  CUDA backend, and the MPI and Charm++ drivers.
- `src/bhlab/logs/` owns the event schema, source adapters, SQLite store,
  queries, keyword extraction, baseline statistics, rules, and the watcher.
- `src/bhlab/demo.py` orchestrates the acceptance story. It does not implement a
  second copy of any feature.

## Data and control flow

A run starts with a `RunSpec`. The planner resolves it into a `LaunchPlan`,
which names the binary, argv, environment, and a human-readable reason. The
runner creates the output directory, invokes the plan, and writes `run.json`
next to the output. The native program writes `events.jsonl` in the same run
directory.

`LogEvent` is the shared record between the framework and the watcher. The
native `EventLogger` emits `run_start`, `phase_end`, `shuffle_end`, `verify`,
and `run_end`. Python adapters normalize application, Slurm, and syslog lines
into the same fields.

`baseline.build` groups completed jobs by signature and stores median, MAD, and
p95 for duration per GB and RSS per GB. `watcher` keeps a ring buffer per job.
When a rule fires, the alert stores the recent events as evidence. SQLite holds
events and alerts. `alerts.jsonl` is the append-only external record.

## Core structures

| Structure | Key fields | Owner |
|---|---|---|
| `RunSpec` | app, input, output, comm, device, layout, nodes, ranks, k | `planner.py` |
| `LaunchPlan` | comm, device, layout, launcher, argv, reason, binary | `planner.py` |
| `SeqBatch` | layout, ids, seqs or packed, lengths, skipped_reads | `types.hpp` |
| `PipelineSpec` | app, input, output, events, k, layout, device, steps | `types.hpp` |
| `LogEvent` | ts, source, job_id, host, event, level, message, params | `logs/schema.py` |
| `Baseline` | signature, n, median, MAD, p95 | `logs/baseline.py` |
| `Alert` | rule_id, job_id, severity, message, evidence | `logs/watch.py` |

## Invariants

- Same input, app, and `k` produce the same SHA-256 across `aos8` and `soa2`,
  across local and MPI, and across CPU and GPU once CUDA is verified.
- Every run path writes the same `LogEvent` schema.
- Backend selection is deterministic and lives only in the planner.
- The generated code uses only public headers under `native/include/bhlab/`.
- The tool does not submit Slurm jobs.

## External dependencies

- Python: Typer, Jinja2, `tomli` on Python 3.10.
- C++: C++17 standard library, zlib, and optional OpenMP, MPI, Charm++, and CUDA.
  Charm++ uses `charmrun` on classic builds and `prterun` on reconverse builds.
- Libraries probed at build time: zlib, libdeflate, bzip2, lzma, htslib.
- Storage: SQLite through the Python standard library.
- Slurm command-line tools are optional and read-only.

## Quality attributes

- Determinism is enforced by sorted k-mer output and checksum comparisons.
- Reviewability comes from `bhlab demo acceptance` and
  `scripts/acceptance.sh`, which write an evidence directory.
- Portability comes from one kernel core and thin backend adapters. The MPI and
  Charm++ drivers are compiled and tested. The CUDA driver shares the same core
  and is the remaining verification work.
- Low cost comes from using the standard library, SQLite, generated Makefiles,
  and a line-based DSL instead of a compiler.

## Decisions

See the [architecture decision records](adr/README.md).
