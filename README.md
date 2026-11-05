# BioHPC_Lab_CLI

BioHPC Lab is a CLI for running small bioinformatics HPC workloads and inspecting
runtime events. It counts canonical k-mers and computes minimizer sketches from
sequencing reads, generates C++ pipeline drivers, benchmarks execution layouts,
and detects log anomalies using rules and per-workload baselines.

K-mer counting supports local, MPI, and Charm++ communication paths. Minimizer
sketching currently uses the local path. The tool can emit a Slurm script and read
Slurm logs, but it does not submit jobs. It is a standalone lab tool, not a
scheduler or a production platform.

## Getting started

Common prerequisites for all build profiles:

- Python 3.10 or newer and `uv` for the CLI and Python dependencies.
- GNU Make, a C++17 compiler, and zlib development headers and libraries for
  the native build.

Install the compiler and backend components required by your selected profile:

| Build profile | Compiler and backend requirements |
| --- | --- |
| Local CPU (`local-clang`) | A C++17 compiler available as `c++`. |
| CPU with OpenMP (`cpu-gcc`) | `g++` with OpenMP support and its runtime. |
| MPI (`mpi-clang`) | `clang++`, an MPI compiler wrapper `mpicxx`, and `mpirun` on `PATH`. |
| Charm++ (`charm-clang`) | `clang++`, `charmc`, and a matching `charmrun` or `prterun` launcher. |
| CUDA (`gpu-cuda`) | An NVCC-compatible `g++` with OpenMP support and its runtime, CUDA toolkit and runtime libraries, a visible GPU, and `nvcc` and `nvidia-smi` on `PATH`. |

Clone the repository and run the remaining commands from its root:

```sh
git clone https://github.com/Antidington/BioHPC_Lab_CLI.git
cd BioHPC_Lab_CLI
```

Optionally create an environment from the provided [mamba YAML](environment.yml).
It includes GNU Make, GCC, Clang 19, Charm++, Open MPI, CUDA 12.8 build components,
and the external libraries.
Skip this step if your existing environment already provides the dependencies.
The helper first builds the local Charm++ package consumed by mamba.

```sh
bash scripts/build_charm_conda.sh
mamba env create --prefix "$PWD/build/_deps/bhlab-depns" -f environment.yml
mamba activate "$PWD/build/_deps/bhlab-depns"
export PKG_CONFIG_PATH="$CONDA_PREFIX/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
```

The `bhlab-depns` prefix belongs to the current worktree. Create a separate prefix in
each worktree used for testing.

See [environment setup](CONTRIBUTING.md#set-up) for details. Install the Python
dependencies with `uv`, then check the environment and build the local CPU example:

```sh
uv sync --extra dev
uv run bhlab doctor
uv run bhlab build --platform local-clang
```

`doctor` reports detected compilers, runtimes, devices, and libraries; it does
not install system dependencies. The build generates a Makefile and native
binaries on the target host.

Count k-mers in the bundled FASTQ fixture:

```sh
uv run bhlab run \
  --input fixtures/reads/tiny.fq \
  --output runs/demo/counts.tsv \
  --app kmer --comm local --device cpu --layout aos8 --k 15
head runs/demo/counts.tsv
```

The TSV contains `kmer` and `count` columns. Each count combines a k-mer and
its reverse complement under their canonical representation. The command also
writes `runs/demo/events.jsonl` and `runs/demo/run.json`; the latter records
the launch plan, return code, and output SHA-256.

## Work with reads

Input is FASTA or FASTQ, optionally gzip-compressed with a `.gz` suffix when
zlib is available. This is a limited FASTX reader, not full format coverage:
FASTQ records must have one sequence line and one quality line. An entire read
containing bases other than A, C, G, and T is skipped. Use uppercase bases with
`aos8`; BAM and CRAM are outside the supported scope. `k` must be between 1 and
31. See the [CLI reference](docs/reference/cli.md) for the remaining options.

To compute local minimizers on the same fixture:

```sh
uv run bhlab run \
  --input fixtures/reads/tiny.fq \
  --output runs/minimizer/minimizers.tsv \
  --app minimizer --comm local --device cpu --layout aos8 --k 15 --window 8
```

The output has `read_id`, `pos`, `kmer`, and `hash` columns. `read_id` is the
zero-based index among accepted reads, not the FASTQ identifier. `pos` is the
window start, not the position of the selected k-mer. When a read has fewer
k-mers than the window, the implementation outputs its first canonical k-mer
at position zero. `hash` is the encoded canonical k-mer value.

### Compare layouts

```sh
uv run bhlab bench \
  --input fixtures/reads/tiny.fq \
  --out evidence/bench \
  --matrix "comm=local;device=cpu;layout=aos8,soa2" --repeat 1 --k 15
```

`evidence/bench/bench.csv` records runtime, throughput, and output checksum for
each cell; `manifest.json` records the environment and matrix. Compare checksums
to check that the two layouts produced the same result for the same input and
parameters. Fixture timings are not a general performance benchmark.

### Run with MPI

An MPI compiler wrapper and `mpirun` are required. For a two-rank test on one
host:

```sh
uv run bhlab build --platform mpi-clang
uv run bhlab run \
  --input fixtures/reads/tiny.fq \
  --output runs/mpi/counts.tsv \
  --app kmer --comm mpi --device cpu --layout aos8 \
  --nodes 2 --ranks-per-node 1 --k 15 --verify-shuffle
```

Here `--nodes 2` requests two ranks; without a cluster allocation this example
does not establish a two-node run. `--verify-shuffle` compares the distributed
count against a serial count. For Charm++ setup, cluster examples, and Slurm
script generation, see the [runbook](docs/operations/runbook.md).

## Inspect logs and alerts

The log pipeline normalizes application JSONL, Slurm output, syslog, and text
sources into SQLite. It supports queries, keyword extraction, replay, and live
watching. Rules can flag conditions such as OOM messages and nonzero exits;
baseline rules compare duration and memory per input GB to statistics grouped by
workload signature. By default, a baseline needs at least eight samples per
signature. Supply a history of normal completed jobs: baseline construction does
not filter failed jobs automatically.

Build a baseline from the bundled normal history and replay the bundled fault:

```sh
uv run bhlab baseline build \
  --history fixtures/runs/normal --out runs/log-demo/baseline.json
uv run bhlab watch \
  --replay fixtures/logs/fault.jsonl \
  --db runs/log-demo/events.db --baseline runs/log-demo/baseline.json
uv run bhlab alert list --db runs/log-demo/events.db
```

The replay writes alerts and preceding-event evidence to the SQLite database
and `runs/log-demo/alerts.jsonl`. These alerts are rule and baseline findings,
not proof of the cause of a failure. See the [log schema](docs/reference/log-schema.md),
[CLI reference](docs/reference/cli.md), and [configuration reference](docs/reference/configuration.md)
for sources, live watching, alert inspection, and webhook configuration.

## Pipeline generation and acceptance demo

The line-based [pipeline DSL](docs/reference/pipeline-dsl.md) describes steps
such as `scatter_reads`, `shuffle_kmers`, and `gather_stats` and generates local,
MPI, or Charm++ drivers that use the shared native core. The runbook contains
[build and run instructions](docs/operations/runbook.md#generate-a-driver).

```sh
uv run bhlab demo acceptance
```

The local demo builds and runs the tools, compares checksums, generates a driver,
builds a baseline, normalizes logs, and replays a fault. Results are written to
`evidence/<timestamp>/`, including `SUMMARY.md`, benchmark results, a baseline,
and alerts. **The demo deletes and recreates `runs/demo-normal` if it already
exists.**

## Verification and limitations

The [project status](docs/project/status.md) records functional checks of local
CPU, two-rank MPI, two-PE Charm++, and CUDA k-mer counting on the designated
hosts, including generated drivers and both layouts, verified on 2026-11-01.
Multi-node execution and performance portability remain unverified. The MPI
driver reads the full input on every rank. Use the status page for the evidence
scope and known monitoring limitations.

## Documentation

- [CLI reference](docs/reference/cli.md) and [configuration reference](docs/reference/configuration.md)
- [Operational runbook](docs/operations/runbook.md) and [pipeline DSL](docs/reference/pipeline-dsl.md)
- [Architecture overview](docs/architecture/overview.md) and [documentation index](docs/index.md)
- [Contributing and development checks](CONTRIBUTING.md)

## License

[MIT](LICENSE).
