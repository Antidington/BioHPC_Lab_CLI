# Project Status

- Status: Working local, MPI, and Charm++ build; CUDA and multi-node pending
- Owner: BioHPC Lab
- Scaffold created: 2026-10-22
- Last verified: 2026-10-22

## Current release or milestone

`0.1.0` covers the local CPU path, the two-rank MPI path, the two-PE Charm++
path, generated local, MPI, and Charm++ drivers, the benchmark harness, the
three-source log pipeline, baseline learning, and fault replay.

## Working capabilities

| Capability | State | Evidence | Verified on |
|---|---|---|---|
| Local k-mer counting | Working | `bhlab run --comm local` writes sorted counts | 2026-10-22 |
| Local minimizer sketching | Working | `bhlab demo acceptance` writes `runs/minimizer/minimizer.tsv` | 2026-10-22 |
| `aos8` and `soa2` equality | Working | Both layouts produced the same SHA-256 in `bench/bench.csv` | 2026-10-22 |
| MPI two-rank shuffle | Working | `bhlab-kmer-mpi --verify-shuffle` wrote `verify.match=1`; checksum matched local | 2026-10-22 |
| Charm++ two-PE reduction | Working | `bhlab run --comm charm --nodes 2` matched the local checksum through `prterun` | 2026-10-22 |
| Generated local driver | Working | `build/bin/kmer_qc` matched the hand-written checksum | 2026-10-22 |
| Generated MPI driver | Working | `build/bin/kmer_qc_mpi` matched the local checksum on two ranks | 2026-10-22 |
| Generated Charm++ driver | Working | `build/bin/kmer_qc_charm` matched the local checksum on two PEs | 2026-10-22 |
| Five library probes | Working | `bhlab deps probe` found zlib, libdeflate, bzip2, lzma, htslib | 2026-10-22 |
| CPU and GPU Makefiles | Emitted | `build/Makefile.cpu-gcc`, `build/Makefile.gpu-cuda` | 2026-10-22 |
| Three log sources | Working | `log stats` reported app, slurm, and syslog | 2026-10-22 |
| Baseline and alert replay | Working | `bhlab demo acceptance` wrote three alerts with evidence | 2026-10-22 |
| Python tests | Passing | `uv run pytest` reported 23 passed | 2026-10-22 |
| Native core test | Passing | `make -f build/Makefile.local-clang check` printed `core tests passed` | 2026-10-22 |
| Acceptance script | Passing | `scripts/acceptance.sh` completed the local demo and the two-rank MPI check | 2026-10-22 |
| Full acceptance demo | Passing | `bhlab demo acceptance --full` reported `{'mpi': True, 'charm': True}` and included Charm++ and MPI rows in `bench.csv` | 2026-10-22 |

## In progress

CUDA is implemented but not compiled here because this host has no `nvcc` and no
NVIDIA device. The GPU kernel and the `gpu-cuda` binary are not verified. The
local, MPI, and Charm++ paths are verified on one host.

## Blockers and risks

- CUDA device availability and the selected `sm_` value. Set `cuda_arch` in
  `platforms/gpu-cuda.toml` to match the cluster GPU.
- Multi-node runs have not used a real interconnect. The two-rank MPI and
  two-PE Charm++ runs used one host. Record the two-node checksums before
  claiming cross-node performance.
- The MPI driver reads the full input on every rank. This is correct for the
  fixture but wastes I/O at scale. The roadmap keeps a split-reader as a later
  optimization.
- The Charm++ launcher differs by build. Classic Charm++ uses `charmrun +p N`.
  The reconverse build used here uses `prterun -n N`. The planner supports both.

## Known operational state

The development host is macOS with Python 3.12, Open MPI 5, a local Charm++
reconverse build, and all five libraries. It has no CUDA and no Slurm. Charm++
lives outside the repository at `/tmp/charm/reconverse-darwin-arm8` and is not a
project dependency. The local, MPI, and Charm++ paths are the ones exercised
here.

## Next review

Re-run the full acceptance on the cluster and replace the pending CUDA and
multi-node rows with two-node CPU, GPU, and Charm++ results.
