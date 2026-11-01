# Product Requirements

- Status: Accepted
- Owner: BioHPC Lab
- Scaffold created: 2026-10-22
- Last verified: 2026-10-22; platform evidence refreshed 2026-11-01

## User scenarios

1. Build and run a k-mer workload locally, then repeat it on two MPI ranks and
   compare the checksums.
2. Generate a driver from a pipeline file, compile it, and run it against the
   same input.
3. Replay a normal history, build a baseline, replay an out-of-memory fault, and
   show the alert with the events that came before it.
4. Watch a live run directory and receive a webhook when a job exceeds its
   learned duration or memory envelope.
5. Generate a CPU and a GPU Makefile on the same host and inspect the detected
   libraries and flags.

## Functional requirements

Statuses are `Verified`, `Partial`, or `Proposed`. `Verified` means a command in
this repository produced the stated evidence. Unless dated otherwise below,
records are from 2026-10-22. The [project status](../project/status.md) owns the
2026-11-01 designated-host platform evidence and its limits.

| ID | Requirement | Acceptance criteria | Status |
|---|---|---|---|
| FR-001 | Run one software on two compute platforms with performance portability | CPU local and MPI runs produce the same checksum; GPU source exists and is built by `gpu-cuda`; benchmark CSV records both | Partial; CPU/GPU functional equality verified 2026-11-01, performance portability pending |
| FR-002 | Provide two memory layouts for different devices | `aos8` and `soa2` produce identical k-mer counts; benchmark records bytes and throughput | Verified |
| FR-003 | Support MPI and Charm++ drivers with parameter selection | `--comm auto` prints the selected backend and reason; explicit unavailable backend fails; MPI and Charm++ runs work | Verified on one host |
| FR-004 | Implement one cross-node common communication algorithm | `KmerShuffle` partitions by hash, exchanges, merges, and matches serial output | Verified on one host with 2 MPI ranks and 2 Charm++ PEs; cross-node verification pending |
| FR-005 | Define one domain data type and two common algorithms | `SeqBatch` is the input type; k-mer counting and minimizer sketching both write deterministic output | Verified locally; k-mer verified on MPI and Charm++ |
| FR-006 | Support two domain communication keywords and generate executable code | `scatter_reads` and `shuffle_kmers` render to C++; local, MPI, and Charm++ drivers compile and match the hand-written checksum | Verified |
| FR-007 | Auto-configure five libraries and generate two platform Makefiles | `deps probe` finds zlib, libdeflate, bzip2, lzma, and htslib; `build --emit-only` writes CPU and GPU Makefiles | Verified |
| FR-008 | Support three log sources | Application JSONL, Slurm output, and syslog normalize into one database | Verified |
| FR-009 | Use one format with time, parameters, and event | `log validate` accepts exported JSONL; every row has `ts`, `event`, and `params` | Verified |
| FR-010 | Sort, filter, and extract anomaly keywords | `log query` sorts and filters; `log keywords` ranks terms against the rest of the corpus | Verified |
| FR-011 | Build a normal model from historical jobs | `baseline build` writes median, MAD, and p95 per signature with at least 8 samples | Verified |
| FR-012 | List events before an anomaly | `alert show` prints the preceding events and timestamps | Verified |
| FR-013 | Detect anomalies in real time and alert | Replay raises alerts; live tailing and webhook delivery are implemented | Partial, live cluster delivery unverified |

## Non-functional requirements

| ID | Requirement | Measure | Status |
|---|---|---|---|
| NFR-001 | Deterministic results | Same input, app, and `k` produce the same SHA-256 across layouts and backends | Verified 2026-11-01 for CPU/GPU layouts, MPI, and Charm++ on one host |
| NFR-002 | Single CLI | Every workflow starts with `bhlab`; native binaries are implementation details | Verified |
| NFR-003 | No scheduler | The tool never calls `sbatch`; `--emit-slurm` only writes a script | Verified by code review |
| NFR-004 | Low dependency surface | Python dependencies are Typer, Jinja2, and `tomli` on Python 3.10 | Verified |
| NFR-005 | Fast local feedback | `uv run pytest` completes in under 5 seconds on the development host | Verified |
| NFR-006 | Evidence for review | `bhlab demo acceptance` writes summary, checksums, CSV, baseline, and alerts | Verified |
| NFR-007 | Failure is explicit | Missing MPI, Charm++, CUDA, or a binary produces a named error, not a silent fallback | Verified for MPI; CUDA masked-device failure verified 2026-11-01 |

## Dependencies and constraints

- Python 3.10 or newer. The repository uses `uv` and `uv.lock`.
- A C++17 compiler and zlib for the local backend.
- Open MPI or MPICH for the MPI backend.
- Charm++ for the Charm++ backend.
- CUDA toolkit and an NVIDIA device for the GPU backend.
- Slurm command-line tools for reading `sacct` and `squeue` output. The tool
  does not require Slurm for local or MPI runs.

## Verification evidence

- The 2026-11-01 designated-host regression passed all 48 master checks and
  seven CUDA hardware tests. The raw GPU suite retained one extra alert-gate
  failure; its adjudication and the separate ingestion check are recorded in
  [project status](../project/status.md). Multi-node and performance evidence
  remain pending.

Historical evidence from 2026-10-22 follows.

- `uv run pytest` passes 23 tests.
- `uv run bhlab demo acceptance --full` writes
  `evidence/<timestamp>/SUMMARY.md` with matching local, MPI, Charm++, and
  generated-driver checksums, `backend checks: {'mpi': True, 'charm': True}`,
  and three alerts.
- A two-rank MPI run compares its result to a serial count and writes
  `verify.match=1`.
- A two-PE Charm++ run matches the local checksum through `prterun`.
- `uv run bhlab doctor` detects all five libraries on the development host.
