# Tutorials

## Build and run a portable k-mer job

In this tutorial, you build the local tool, run a k-mer count on the fixture
reads, compare two memory layouts, and replay a fault into an alert. The whole
sequence takes a few minutes on a laptop.

### Install and check

```sh
uv sync --extra dev
uv run bhlab doctor
```

You should see `mpi: yes` or `mpi: no`, `cuda: no` on a laptop, and a library
line for each of the five probes. A missing library is reported, not installed.

### Build and run

```sh
uv run bhlab build --platform local-clang
uv run bhlab run \
  --input fixtures/reads/tiny.fq \
  --output runs/tutorial/counts.tsv \
  --app kmer --comm local --device cpu --layout aos8 --k 15
```

The command prints `exit: 0` and a SHA-256. Open `runs/tutorial/counts.tsv`.
The first line is `kmer	count`, and the rows are sorted by k-mer.

Run the same input with `--layout soa2`. The checksum must stay the same. The
`soa2` path stores two bits per base and reads differently from `aos8`, but the
counts are layout independent.

### Compare with MPI

If `doctor` reported MPI, build the MPI profile and run two ranks:

```sh
uv run bhlab build --platform mpi-clang
uv run bhlab run \
  --input fixtures/reads/tiny.fq \
  --output runs/tutorial-mpi/counts.tsv \
  --comm mpi --nodes 2 --ranks-per-node 1 --k 15 --verify-shuffle
```

The run event contains `verify` with `match: 1`. The checksum matches the local
run.

### Generate a driver

```sh
uv run bhlab codegen pipelines/kmer_qc.bhl --comm local
uv run bhlab build --platform local-clang
./build/bin/kmer_qc --input fixtures/reads/tiny.fq \
  --output runs/tutorial-generated/counts.tsv \
  --events runs/tutorial-generated/events.jsonl --k 15 --layout aos8
```

The generated binary writes the same counts as the hand-written app.

### Replay a fault

Build a normal baseline from ten tiny runs:

```sh
for i in $(seq 0 9); do
  uv run bhlab run --input fixtures/reads/tiny.fq \
    --output runs/tutorial-normal/$i/counts.tsv \
    --app kmer --comm local --k 15 --layout aos8 --job-id normal-$i
done
uv run bhlab baseline build --history runs/tutorial-normal --out baselines/tutorial.json
```

Normalize the three log sources and replay the fault:

```sh
uv run bhlab log normalize \
  --source app:fixtures/logs/fault.jsonl \
  --source slurm:fixtures/logs/slurm_job.out \
  --source syslog:fixtures/logs/syslog.txt \
  --db var/tutorial.db
uv run bhlab watch --replay fixtures/logs/fault.jsonl \
  --db var/tutorial.db --baseline baselines/tutorial.json
uv run bhlab alert list --db var/tutorial.db
```

You should see three alerts: an OOM keyword match, a baseline deviation, and a
non-zero exit code. `bhlab alert show 1 --db var/tutorial.db` prints the events
that came before the failure.

To run the same story automatically and write an evidence bundle, use
`uv run bhlab demo acceptance`.
