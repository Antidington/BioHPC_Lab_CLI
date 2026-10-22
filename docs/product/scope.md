# Project Scope

- Status: Accepted
- Owner: BioHPC Lab
- Scaffold created: 2026-10-22
- Last verified: 2026-10-22

## Problem and desired outcome

A small bioinformatics team needs a demonstrable HPC tool that covers portable
kernels and runtime anomaly detection without building a platform. The tool must
run on a laptop and on a Slurm cluster, produce acceptance evidence from real
runs, and stay separate from the production platform.

The outcome is one CLI, `bhlab`, with a shared C++ kernel, two thin
communication drivers, generated build files, and an event pipeline that learns
normal behavior from completed jobs.

## In scope

- Canonical k-mer counting and minimizer sketching on sequencing reads.
- `aos8` and `soa2` memory layouts with identical results.
- Local, MPI, and Charm++ launch paths. The backend is selected by
  configuration, not by editing code.
- Hash-partitioned k-mer shuffle across ranks.
- A line-based pipeline DSL with `scatter_reads`, `shuffle_kmers`, and
  `gather_stats`, rendered into C++ drivers.
- Auto-detection of zlib, libdeflate, bzip2, lzma, and htslib.
- Generated Makefiles for `local-clang`, `mpi-clang`, `cpu-gcc`, and
  `gpu-cuda`.
- Normalization of application JSONL, Slurm output, and syslog sources into one
  event schema.
- SQLite event queries, keyword extraction, robust baselines, and alert rules.
- Replay and live tailing, with console, JSONL, and webhook alerts.
- Acceptance evidence under `evidence/<timestamp>/`.

## Out of scope and non-goals

- A scheduler, job submission service, or multi-tenant platform.
- A custom MPI, Charm++, or CUDA runtime.
- A web console, user accounts, or role-based access.
- Kafka, Elasticsearch, ClickHouse, or a metrics server.
- Deep learning or learned anomaly models.
- Automatic parameter search beyond the fixed benchmark matrix.
- Multi-GPU, RDMA tuning, checkpointing, or task migration.
- Full FASTA, FASTQ, BAM, and CRAM coverage. Reads with bases outside A, C, G,
  and T are skipped.
- Integration with the production platform. The tool stays standalone.
- Windows and macOS native performance work. Linux HPC is the target.

## Users and primary use cases

- A bioinformatics engineer checks the environment, builds a CPU or GPU binary,
  and runs a k-mer workload on two nodes.
- A reviewer runs one command and sees checksum equality, generated code, and a
  fault alert with preceding events.
- An operator points `bhlab watch` at a run directory and receives a webhook
  when a job exceeds its learned duration or memory baseline.
- A developer regenerates a driver from a pipeline file and compiles it with the
  same framework.

## Constraints and assumptions

Confirmed constraints:

- Linux HPC target with Slurm, MPI, Charm++, and optionally CUDA.
- Python 3.10 or newer, managed with `uv`.
- C++17 compiler and zlib on the build host.
- The tool must not submit Slurm jobs. It may emit a script and read Slurm logs.
- Low development cost is a first-class requirement.

Assumptions that need cluster confirmation:

- The cluster provides Open MPI or MPICH and a Charm++ installation. Classic
  Charm++ uses `charmrun`. The reconverse build uses `prterun`.
- GPU nodes provide CUDA 11 or newer and a compute capability supported by the
  selected `sm_` value.
- `htslib`, `libdeflate`, `bzip2`, and `lzma` development headers are present on
  the acceptance host.
- Charm++ behaves the same on the cluster as the local two-PE build. The local
  build is verified. Multi-node Charm++ remains unverified until a cluster run
  is recorded.

## Success criteria

The tool meets the project indicators when all of these are true:

1. One software runs on two compute platforms and produces identical results.
2. Two layouts exist for different devices and pass the same golden checksum.
3. MPI and Charm++ are selectable by configuration, with a printed reason.
4. A cross-node k-mer shuffle is implemented and compared to a serial count.
5. `SeqBatch` is the domain type, and k-mer counting plus minimizer sketching
   are both implemented.
6. At least two domain communication keywords generate compilable code.
7. Five libraries are auto-detected and two platform Makefiles are generated.
8. Three log sources normalize into one schema.
9. The schema contains time, parameters, and event fields.
10. Events can be sorted, filtered, and mined for anomaly keywords.
11. A normal baseline is learned from historical jobs.
12. An alert carries the events that preceded it.
13. A replayed or live fault produces an alert within the demo window.

## Related requirements and decisions

- [Requirements](requirements.md)
- [Architecture](../architecture/overview.md)
- [Architecture decisions](../architecture/adr/README.md)
- [Status](../project/status.md)
