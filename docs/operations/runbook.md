# Runbook

- Owner: BioHPC Lab
- Scaffold created: 2026-10-22
- Last verified: 2026-10-22

## Check the environment

```sh
uv sync --extra dev
uv run bhlab doctor
```

`doctor` reports MPI, Charm++, CUDA, OpenMP, Slurm, compilers, and the five
libraries. A missing runtime is reported as missing. The tool does not install
system packages.

## Build

Local macOS or Linux host:

```sh
uv run bhlab build --platform local-clang
```

One host with Open MPI:

```sh
uv run bhlab build --platform mpi-clang
```

Linux HPC CPU nodes:

```sh
uv run bhlab build --platform cpu-gcc
```

Charm++ on one host:

```sh
export PATH=/path/to/charm/bin:$PATH
uv run bhlab build --platform charm-clang --with-charm
```

GPU nodes:

```sh
uv run bhlab build --platform gpu-cuda
```

To inspect the generated files without compiling:

```sh
uv run bhlab build --platform cpu-gcc --emit-only
uv run bhlab build --platform gpu-cuda --emit-only
```

Each platform writes `build/Makefile.<platform>` and
`build/config.<platform>.mk`. The config file lists the detected libraries and
feature flags.

## Run

Local:

```sh
uv run bhlab run \
  --input fixtures/reads/tiny.fq \
  --output runs/local/counts.tsv \
  --app kmer --comm local --device cpu --layout aos8 --k 15
```

Two MPI ranks on one host:

```sh
uv run bhlab run \
  --input fixtures/reads/tiny.fq \
  --output runs/mpi/counts.tsv \
  --app kmer --comm mpi --nodes 2 --ranks-per-node 1 \
  --k 15 --layout aos8 --verify-shuffle
```

Charm++ on one host, with the launch command selected from the installed
launcher:

```sh
uv run bhlab run \
  --input fixtures/reads/tiny.fq \
  --output runs/charm/counts.tsv \
  --comm charm --nodes 2 --k 15 --layout aos8
```

The planner uses `charmrun +p N` when `charmrun` exists. It uses `prterun -n N`
for a reconverse build. If neither exists, the command fails before launching.

Print the resolved command without running it:

```sh
uv run bhlab run --input fixtures/reads/tiny.fq --output /tmp/x.tsv --dry-run
```

Write a Slurm script without submitting it:

```sh
uv run bhlab run --input fixtures/reads/tiny.fq --output runs/slurm/counts.tsv \
  --comm mpi --nodes 2 --emit-slurm runs/slurm/job.sbatch
```

## Generate a driver

```sh
uv run bhlab codegen pipelines/kmer_qc.bhl --comm local
uv run bhlab build --platform local-clang
./build/bin/kmer_qc --input fixtures/reads/tiny.fq \
  --output runs/generated/counts.tsv --events runs/generated/events.jsonl \
  --k 15 --layout aos8
```

For MPI, generate with `--comm mpi`, build the `mpi-clang` profile, and run
`build/bin/kmer_qc_mpi` with `mpirun`. For Charm++, generate with `--comm charm`,
build `charm-clang --with-charm`, and run `build/bin/kmer_qc_charm` with
`charmrun` or `prterun`.

## Benchmark

```sh
uv run bhlab bench \
  --input fixtures/reads/tiny.fq \
  --out evidence/bench \
  --matrix "comm=local,mpi;device=cpu;layout=aos8,soa2;nodes=1,2" \
  --repeat 3 --k 15 --allow-missing
```

The output is `bench.csv`, `manifest.json`, and one run directory per cell.
`--allow-missing` records unavailable combinations as `skipped` instead of
failing the whole matrix.

## Logs

Normalize three sources:

```sh
uv run bhlab log normalize \
  --source app:fixtures/logs/fault.jsonl \
  --source slurm:fixtures/logs/slurm_job.out \
  --source syslog:fixtures/logs/syslog.txt \
  --db var/events.db
```

Query and inspect:

```sh
uv run bhlab log stats --db var/events.db
uv run bhlab log query --db var/events.db --grep OOM --sort ts
uv run bhlab log keywords --db var/events.db --job fault-001 --top 10
uv run bhlab log export --db var/events.db --out var/events.jsonl
uv run bhlab log validate var/events.jsonl
```

## Baseline and alerts

Build a baseline from completed job events:

```sh
uv run bhlab baseline build --history runs/normal --out baselines/baselines.json
```

Replay a fault:

```sh
uv run bhlab watch \
  --replay fixtures/logs/fault.jsonl \
  --db var/demo.db \
  --baseline baselines/baselines.json
uv run bhlab alert list --db var/demo.db
uv run bhlab alert show 1 --db var/demo.db
```

Live tail:

```sh
uv run bhlab watch \
  --source app:runs/job-1/events.jsonl \
  --source slurm:/var/log/slurm/job-1.out \
  --db var/live.db --baseline baselines/baselines.json --interval 1
```

Set `webhook` in `bhlab.toml` to send a JSON POST for each alert.

## Acceptance

```sh
uv run bhlab demo acceptance
uv run bhlab demo acceptance --full
```

The command writes `evidence/<timestamp>/SUMMARY.md`, `checksums.txt`,
`bench/bench.csv`, `baselines.json`, `events.db`, and `alerts.jsonl`. The
`--full` mode adds MPI, Charm++, and GPU benchmark cells and verifies the
generated MPI and Charm++ drivers. Unavailable backends are recorded as skipped.

## Troubleshooting

| Symptom | Check | Action |
|---|---|---|
| `comm 'mpi' is unavailable` | `which mpicxx mpirun` | Load the MPI module or use `--comm local` |
| `comm 'charm' is unavailable` | `which charmc charmrun prterun` | Load Charm++ or build it with Spack |
| Charm++ binary built but not launched | `which charmrun prterun` | Use a build with a launcher, or add one to `PATH` |
| `device 'gpu' requested but CUDA was not detected` | `which nvcc`, `nvidia-smi` | Run on a GPU node or use `--device cpu` |
| `binary not found` | `ls build/bin` | Run `bhlab build --platform <profile>` |
| `library not found` in the build | `bhlab deps probe` | Load the development package or add its prefix |
| `MPI_ERR_TRUNCATE` | Check the MPI driver build | Rebuild with the current `mpi-clang` or `cpu-gcc` profile |
| Baseline says `insufficient` | `baseline.json` | Collect at least 8 successful runs for the signature |
| No alerts on replay | `bhlab log stats` | Check the baseline signature and the rule keywords |
| Header change is ignored | `build/obj/<platform>` | The Makefile uses `-MMD -MP`; run `bhlab build` again |
