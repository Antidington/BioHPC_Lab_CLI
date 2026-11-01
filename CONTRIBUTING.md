# Contributing

## Set up

Use `uv` for the Python environment.

```sh
uv sync --extra dev
uv run bhlab doctor
```

## Validate

Run the Python tests first.

```sh
uv run pytest
```

Build the local native core and run its C++ tests.

```sh
uv run bhlab build --platform local-clang
make -f build/Makefile.local-clang check
```

Run the end-to-end local story.

```sh
uv run bhlab demo acceptance
```

For MPI on one host, install Open MPI and build the `mpi-clang` profile.

```sh
uv run bhlab build --platform mpi-clang
mpirun --oversubscribe -np 2 ./build/bin/bhlab-kmer-mpi \
  --input fixtures/reads/tiny.fq --output /tmp/mpi.tsv \
  --events /tmp/mpi.jsonl --k 15 --layout aos8 --verify-shuffle
```

For Charm++ on one host, put `charmc` on `PATH` and build the `charm-clang`
profile. Classic Charm++ uses `charmrun`. A reconverse build uses `prterun`.

```sh
export PATH=/path/to/charm/bin:$PATH
uv run bhlab build --platform charm-clang --with-charm
uv run bhlab run --input fixtures/reads/tiny.fq --output /tmp/charm.tsv \
  --comm charm --nodes 2 --k 15 --layout aos8
```

For CUDA hardware tests, use the designated GPU worktree with a working NVIDIA
driver, a visible GPU, `nvcc` and `nvidia-smi` on `PATH`, and CUDA runtime
libraries available to the linker and loader. Install the Python dev dependencies
and build `build/bin/bhlab-kmer` with the `gpu-cuda` profile first. Select an
architecture supported by both the GPU and toolkit. The RTX 5060 Ti uses
`sm_120` and requires a toolkit that supports it, such as CUDA 12.8.

```sh
MAKEFLAGS='-B CUDA_ARCH=sm_120' uv run bhlab build --platform gpu-cuda
BHLAB_TEST_CUDA=1 uv run pytest tests/test_cuda.py
```

These tests compare CPU and GPU counts with an independent reference for both
layouts and require a nonzero exit when CUDA devices are masked. They create
fresh temporary outputs and do not build binaries. Ordinary `pytest` skips
hardware cases without probing the GPU. Once opted in, missing prerequisites
or a nonfunctional CUDA binary fail the tests.

## Layout

- `src/bhlab/` is the Python CLI, planner, build generator, code generation, and
  log pipeline.
- `native/` is the C++17 core, device backends, and communication drivers.
- `platforms/` holds build profiles. A profile produces a Makefile, not a
  second build system.
- `pipelines/` holds the line-based pipeline DSL.
- `rules/` holds anomaly rules.
- `fixtures/` holds deterministic reads and logs.
- `tests/` holds pytest tests.
- `docs/` owns user and design documentation.

## Change rules

- Keep the output checksum identical across layouts, communication backends,
  and devices for the same input and `k`. Add a test when that can break.
- Every run path emits the same `LogEvent` schema.
- Auto selection lives only in `src/bhlab/planner.py`. Do not add backend
  branching inside commands.
- Do not add a scheduler, a custom MPI runtime, a web console, or a machine
  learning model. See the scope document for the current exclusions.
- Update the canonical document when a command, schema, or workflow changes.
  The [documentation index](docs/index.md) names the owner of each topic.

## Regenerate fixtures

```sh
uv run python scripts/make_fixtures.py
```

Fixtures are deterministic. Regenerate them only when the read or log shape
changes, then update the golden expectations.
