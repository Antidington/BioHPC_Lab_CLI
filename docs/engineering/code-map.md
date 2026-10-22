# Code Map

- Owner: BioHPC Lab
- Scaffold created: 2026-10-22
- Last verified: 2026-10-22

## Entry points

- `src/bhlab/cli.py` defines the `bhlab` command surface. It wires Typer
  subcommands to the planner, build, codegen, bench, and log modules.
- `src/bhlab/__main__.py` allows `python -m bhlab`.
- `native/apps/kmer_main.cpp` is the local k-mer binary.
- `native/apps/minimizer_main.cpp` is the local minimizer binary.
- `native/apps/kmer_mpi_main.cpp` is the MPI k-mer binary.
- `native/src/comm/charm_driver.cpp` contains the Charm++ mainchare and chare
  array.

## Python modules

| Path | Owns |
|---|---|
| `config.py` | `bhlab.toml` defaults and path resolution |
| `capabilities.py` | compiler, MPI, Charm++, CUDA, Slurm, and library probes |
| `planner.py` | `RunSpec` to `LaunchPlan`, auto selection, Slurm script text |
| `build.py` | platform Makefile and config generation, make invocation |
| `deps.py` | platform profiles, Makefile template, library flags |
| `codegen.py` | pipeline parser and Jinja2 rendering |
| `runner.py` | subprocess execution, `run.json`, checksums |
| `bench.py` | parameter matrix, CSV, manifest, median table |
| `demo.py` | acceptance orchestration and evidence summary |
| `logs/schema.py` | `LogEvent` validation and JSON conversion |
| `logs/sources.py` | app, Slurm, syslog, and text line adapters |
| `logs/store.py` | SQLite schema, inserts, queries, alerts, export |
| `logs/normalize.py` | source expansion and ingestion |
| `logs/keywords.py` | term frequency ratio and anomaly word marking |
| `logs/baseline.py` | job collection, signature grouping, robust statistics |
| `logs/rules.py` | TOML rule loading and event evaluation |
| `logs/watch.py` | ring buffer, tailing, dedupe, evidence, webhook |

## Native modules

| Path | Owns |
|---|---|
| `native/include/bhlab/types.hpp` | `SeqBatch`, `KmerCount`, `Minimizer`, `PipelineSpec` |
| `native/include/bhlab/layout.hpp` | layout conversion, k-mer encoding, TSV writers |
| `native/include/bhlab/kmer.hpp` | CPU and GPU count entry points |
| `native/include/bhlab/minimizer.hpp` | minimizer entry point |
| `native/include/bhlab/events.hpp` | JSONL event logger |
| `native/include/bhlab/pipeline.hpp` | argument parsing and run entry points |
| `native/src/layout.cpp` | FASTA/FASTQ loading, packing, canonical k-mers |
| `native/src/kmer.cpp` | serial and OpenMP counting, device dispatch |
| `native/src/minimizer.cpp` | sliding-window minimizers |
| `native/src/pipeline.cpp` | local run orchestration and events |
| `native/src/comm/mpi_driver.cpp` | `KmerShuffle`, gather, serial verification |
| `native/src/comm/charm_driver.cpp` | chare array and concatenating reduction |
| `native/src/device/cuda_kernel.cu` | packed k-mer emission and Thrust reduction |

## Generated and runtime artifacts

| Path | Produced by | Notes |
|---|---|---|
| `build/Makefile.<platform>` | `bhlab build` | Not committed |
| `build/config.<platform>.mk` | `bhlab build` | One per platform |
| `build/gen/*_local.cpp` | `bhlab codegen` | Local driver |
| `build/gen/*_mpi.cpp` | `bhlab codegen` | MPI driver |
| `build/gen/*_charm.cpp` and `.ci` | `bhlab codegen` | Charm++ driver |
| `runs/<job>/events.jsonl` | native app | Canonical run events |
| `runs/<job>/counts.tsv` | native app | Sorted k-mer counts |
| `evidence/<timestamp>/` | `bhlab demo` | Acceptance bundle |
| `var/events.db` | `bhlab log normalize` | Default event store |

## Data flow

1. `bhlab run` resolves a `RunSpec` into a `LaunchPlan`.
2. The native app loads reads into a `SeqBatch`, counts k-mers or minimizers,
   writes a sorted TSV, and appends events.
3. `bhlab log normalize` reads application, Slurm, and syslog files into
   `LogEvent` rows.
4. `bhlab baseline build` groups completed jobs and writes robust statistics.
5. `bhlab watch` scores new events and writes alerts with evidence.
6. `bhlab demo acceptance` runs the sequence and copies the artifacts into one
   evidence directory.
