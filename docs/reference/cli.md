# CLI Reference

All commands accept the global `--root PATH` option before the subcommand. The
default root is the current directory. The entry point is `bhlab`, installed by
`uv sync`.

## Project commands

| Command | Options | Behavior |
|---|---|---|
| `bhlab version` | none | Print the package version |
| `bhlab init` | `--force` | Write `bhlab.toml` and create `build`, `runs`, `var`, and `evidence` |
| `bhlab doctor` | `--json` | Print detected runtimes, compilers, and libraries |
| `bhlab deps probe` | `--json` | Print the five library probes |

## Build and run

### `bhlab build`

| Option | Default | Meaning |
|---|---|---|
| `--platform NAME` | `bench.platform` from config | `local-clang`, `mpi-clang`, `charm-clang`, `cpu-gcc`, or `gpu-cuda` |
| `--emit-only` | false | Write `Makefile.<platform>` and `config.<platform>.mk`, do not compile |
| `--jobs N` | 4 | Passed to `make -j` |
| `--with-charm` | false | Also build the framework Charm++ binary |

`build` writes `build/config.<platform>.mk` and
`build/Makefile.<platform>`. The Makefile is the build artifact. The command
returns 1 when `make` fails.

### `bhlab codegen`

| Argument or option | Default | Meaning |
|---|---|---|
| `PIPELINE` | required | A `.bhl` file |
| `--comm local\|mpi\|charm` | `local` | Generated target |
| `--out PATH` | `build/gen/<name>_<comm>.cpp` | Output file; Charm++ also writes a `.ci` |

### `bhlab run`

| Option | Default | Meaning |
|---|---|---|
| `--input PATH` | required | FASTA or FASTQ, optionally gzip |
| `--output PATH` | required | Counts or minimizer TSV |
| `--app kmer\|minimizer` | `kmer` | Algorithm |
| `--comm auto\|local\|mpi\|charm` | `auto` | Communication backend |
| `--device auto\|cpu\|gpu` | `auto` | Device backend |
| `--layout auto\|aos8\|soa2` | `auto` | Memory layout |
| `--nodes N` | 1 | Node count |
| `--ranks-per-node N` | 1 | Ranks per node |
| `--threads N` | 1 | OpenMP threads |
| `--k N` | 21 | k-mer length, 1 to 31 |
| `--window N` | 10 | Minimizer window |
| `--max-reads N` | 0 | Limit reads, 0 means all |
| `--job-id ID` | run directory name | Event job id |
| `--verify-shuffle` | false | Compare MPI counts to a serial count |
| `--dry-run` | false | Print the launch reason and command |
| `--emit-slurm PATH` | none | Write an sbatch script, do not run |

The planner prints its selection reason in `--dry-run` and records it in
`run.json`. An explicit unavailable backend fails. `--comm auto` walks
`comm.order` from `bhlab.toml`.

Charm++ launches with `charmrun +p N` when `charmrun` is on `PATH`. A reconverse
build launches with `prterun -n N`. The tool detects both and fails before
launch when neither exists.

### `bhlab bench`

| Option | Default | Meaning |
|---|---|---|
| `--input PATH` | required | Input reads |
| `--out DIR` | `evidence/bench` | Output directory |
| `--matrix SPEC` | `comm=local;device=cpu;layout=aos8,soa2` | Semicolon-separated groups, comma-separated values |
| `--repeat N` | 3 | Runs per cell |
| `--k N` | 21 | k-mer length |
| `--app kmer` | `kmer` | Benchmark app |
| `--allow-missing` | false | Record unavailable cells as `skipped` |

The output is `bench.csv`, `manifest.json`, and `runs/<cell>/` directories.

## Log commands

### `bhlab log normalize`

`--source SPEC` is repeatable. The prefix is `app`, `slurm`, `syslog`, or
`text`. A directory expands to `.jsonl`, `.log`, `.out`, `.txt`, and gzip
variants.

```sh
bhlab log normalize --source app:runs/job/events.jsonl --source slurm:job.out
```

### `bhlab log query`

Filters are `--job`, `--source`, `--event`, `--level`, `--grep`, `--since`,
`--until`, `--sort`, and `--limit`. `--sort` accepts `ts`, `-ts`, `level`, or
`event`. `--json` prints one JSON object per line.

### `bhlab log keywords`

`--job` scopes the target. `--top` limits the result. The score is the target
term rate divided by the background term rate.

### `bhlab log stats`

Print total events, counts by source, counts by level, and alert count.

### `bhlab log export`

`--out` is required. The export is JSONL in the canonical schema.

### `bhlab log validate`

Validate a JSONL file. The command returns 1 if any line fails the schema.

## Baseline commands

### `bhlab baseline build`

`--history DIR` reads JSONL event files. Without it, the command reads the
SQLite store from `--db`. `--out` defaults to `baselines/baselines.json`.
`--min-samples` defaults to 8.

### `bhlab baseline evaluate`

`--baseline FILE` and `--history DIR` are required. The command prints the
findings for each completed job.

## Watch and alerts

### `bhlab watch`

| Option | Meaning |
|---|---|
| `--config PATH` | Rules TOML, default `rules/default.toml` |
| `--db PATH` | Event store |
| `--baseline PATH` | Baseline JSON |
| `--replay PATH` | Replay a JSONL file |
| `--source SPEC` | Live source, repeatable |
| `--once` | Poll one time |
| `--interval S` | Poll interval |
| `--delay S` | Delay between replay events |

Replay and live sources are mutually exclusive in normal use. Replay is the
deterministic acceptance path. Live tailing starts at the current end of each
file.

### `bhlab alert list`

`--limit` defaults to 50. Alerts are ordered newest first.

### `bhlab alert show ID`

Print the alert, its message, and the preceding events.

## Demo

### `bhlab demo acceptance`

`--full` adds the MPI, Charm++, and GPU benchmark cells and generates the
Charm++ source. Unavailable cells are skipped. Without `--full`, the demo uses
the local CPU backend and two layouts.

The command writes `evidence/<timestamp>/SUMMARY.md` and returns 1 when a
checksum, baseline, source count, or alert check fails.
