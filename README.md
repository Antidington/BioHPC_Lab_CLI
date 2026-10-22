# BioHPC_Lab_CLI

BioHPC Lab is a single-command lab bench for portable bioinformatics kernels. It
runs k-mer counting and minimizer sketching on CPU or GPU, through MPI or
Charm++, and turns the same run events into a learned normal baseline and
real-time alerts.

The tool is independent of the production platform. It can run on a laptop with
the local backend, on a Slurm allocation with `mpirun` or `charmrun`, and later
read Slurm job logs without submitting jobs itself.

## What works now

- Local CPU backend, k-mer counting and minimizer sketching.
- MPI backend, two ranks verified with an identical checksum and serial
  comparison.
- Charm++ backend, two PEs verified with the same checksum through `prterun`.
- Two memory layouts, `aos8` and `soa2`, with identical results.
- Pipeline code generation for local, MPI, and Charm++ targets. All three
  generated drivers compile and run here.
- Five external library probes, plus generated Makefiles for `local-clang`,
  `mpi-clang`, `charm-clang`, `cpu-gcc`, and `gpu-cuda`.
- Three log sources, SQLite normalization, query, keyword extraction, baseline
  learning, fault replay, and alerts.

The CUDA source is implemented but not compiled on this machine. The status
page records that gap.

## Install

```sh
uv sync --extra dev
uv run bhlab doctor
```

The Python environment is managed with `uv`. The native binaries build on the
target machine. A local macOS or Linux machine needs a C++17 compiler and zlib.

## Quick start

```sh
uv run bhlab build --platform local-clang
uv run bhlab run \
  --input fixtures/reads/tiny.fq \
  --output runs/demo/counts.tsv \
  --app kmer --comm local --device cpu --layout aos8 --k 15
uv run bhlab bench \
  --input fixtures/reads/tiny.fq \
  --out evidence/bench \
  --matrix "comm=local;device=cpu;layout=aos8,soa2" --repeat 1 --k 15
```

Run the full local story, including code generation, baseline learning, log
normalization, and fault replay:

```sh
uv run bhlab demo acceptance
```

Evidence lands under `evidence/<timestamp>/`. The demo writes a summary,
checksums, benchmark CSV, baseline JSON, normalized event database, and alerts.

## MPI on one host

```sh
uv run bhlab build --platform mpi-clang
uv run bhlab run \
  --input fixtures/reads/tiny.fq \
  --output /tmp/mpi/counts.tsv \
  --comm mpi --nodes 2 --ranks-per-node 1 --k 15 --verify-shuffle
```

On a cluster, use `--emit-slurm` to write a batch script, then run it inside the
allocation. The tool never calls `sbatch`.

## Charm++ on one host

```sh
export PATH=/path/to/charm/bin:$PATH
uv run bhlab build --platform charm-clang --with-charm
uv run bhlab run \
  --input fixtures/reads/tiny.fq \
  --output /tmp/charm/counts.tsv \
  --comm charm --nodes 2 --k 15 --layout aos8
```

The planner uses `charmrun +p N` when `charmrun` is present and `prterun -n N`
for a reconverse build. Both runners were exercised for the framework binary
and the generated Charm++ driver.

## Documentation

Start with the [documentation index](docs/index.md). The
[CLI reference](docs/reference/cli.md) lists every command. The
[architecture overview](docs/architecture/overview.md) explains the shared
kernel and the two thin communication drivers.

## Status

Local CPU, MPI, Charm++, code generation, benchmarking, and the log pipeline
are verified by tests and recorded evidence. CUDA needs a GPU host to close the
last portability row. See [status](docs/project/status.md) for the exact
commands and results.

## License

MIT. See [LICENSE](LICENSE).
