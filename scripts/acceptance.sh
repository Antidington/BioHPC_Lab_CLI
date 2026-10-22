#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p evidence
uv sync --extra dev
uv run bhlab doctor --json | tee evidence/doctor.json
uv run bhlab build --platform local-clang
make -f build/Makefile.local-clang check
uv run pytest

uv run bhlab demo acceptance "$@"

if command -v mpirun >/dev/null 2>&1 && command -v mpicxx >/dev/null 2>&1; then
  uv run bhlab build --platform mpi-clang
  mpirun --oversubscribe -np 2 ./build/bin/bhlab-kmer-mpi \
    --input fixtures/reads/tiny.fq \
    --output evidence/mpi-counts.tsv \
    --events evidence/mpi-events.jsonl \
    --k 15 --layout aos8 --job-id acceptance-mpi --verify-shuffle
  sha256sum evidence/mpi-counts.tsv
fi

echo "acceptance run complete"
