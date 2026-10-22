# Roadmap

- Owner: BioHPC Lab
- Scaffold created: 2026-10-22
- Last verified: 2026-10-22

## Now

- Keep the local and MPI acceptance path green. Run `uv run pytest`,
  `make -f build/Makefile.local-clang check`, and
  `uv run bhlab demo acceptance` before each handoff.
- Finish the CUDA verification on a GPU host. Record the exact commands and
  checksums under `evidence/`.
- Fill the acceptance matrix with real two-node CPU, Charm++, and GPU numbers.
  The local matrix is a functional check, not a performance claim.
- Keep the generated Makefiles for `cpu-gcc` and `gpu-cuda` in sync with the
  capability probe.

## Next

- Add a Slurm log poller that reads `sacct --json` and `squeue` on a schedule.
  The parser already accepts JSON records. The missing part is a bounded poller
  and a test fixture.
- Add a webhook receiver example for the acceptance room. The watcher already
  sends a JSON POST.
- Add one more domain algorithm only if a reviewer asks. The current two
  algorithms already cover the indicator.

## Later

- Compare `KmerShuffle` against a distributed hash table on a larger read set.
  This is an optimization, not an acceptance requirement.
- Add optional BAM input through htslib. The library is probed and linked, but
  the reader only handles FASTA and FASTQ.
- Add a third build profile for ARM64 if the acceptance host lacks a GPU and a
  second compute platform is still required.

## Explicitly not planned

- A scheduler or a job submission service.
- A web console, accounts, or role-based access.
- A custom MPI, Charm++, or CUDA runtime.
- A general DSL compiler.
- Deep learning anomaly detection.
- Multi-GPU, RDMA tuning, checkpointing, or task migration.
- Production platform integration.

See [scope](../product/scope.md) for the standing exclusions.
