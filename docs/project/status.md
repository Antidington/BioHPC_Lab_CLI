# Project Status

- Status: Local, MPI, Charm++, and CUDA functional checks passed; multi-node pending
- Owner: BioHPC Lab
- Scaffold created: 2026-10-22
- Last verified: 2026-11-01

## Current release or milestone

`0.1.0` covers local CPU and CUDA k-mer counting, the two-rank MPI path, the
two-PE Charm++ path, generated drivers, the benchmark harness, the three-source
log pipeline, baseline learning, and fault replay.

## Designated-host verification on 2026-11-01

The tested code revision is `084ad51f0b136f42ced6a424037be3dd2d1a9422`.
The existing isolated test worktrees were reused at the user's request.

| Platform | Host and worktree | Verified scope |
|---|---|---|
| `local-clang` | `master`, `/pmaster/wenjichen/BioHPC_Lab_CLI-worktrees/e2e-20261030-0910-master` | Forced build, native core, k-mer `k=1,15,31`, both layouts, generated driver, minimizer, local demo |
| `mpi-clang` | Same `master` worktree | Forced build, two ranks on one host, both layouts, serial shuffle verification, generated driver |
| `charm-clang` | Same `master` worktree | Forced build, two PEs on one host, both layouts, generated driver |
| `gpu-cuda` | `5060ti`, `/mnt/d/projects/BioHPC_Lab_CLI-worktrees/e2e-20261030-0910-gpu` | Forced CLI build without an NVCC include override, RTX 5060 Ti, NVCC 12.8.93, `sm_120`, both layouts, `k=1,15,31`, generated driver, masked-device failure |

All 48 master checks passed. GPU hardware pytest reported seven passed; ordinary
pytest on each host reported 23 passed and seven hardware skips. K-mer outputs
matched an independent string oracle. The four CPU/GPU benchmark cells matched
checksums; these short runs establish functional equality only. CUDA header
dependency checks observed rebuild required after a header timestamp change.

The raw GPU suite remains **FAIL, 61 of 62 checks passed**. Its extra
`cuda-failure-alert` assertion expected an exit alert from an error-only native
stream. Independent review rejected that expectation under the existing event
contract. A separate read-only check confirmed exact event ingestion and the
default rule behavior. Both known CUDA repair criteria passed. Original results
are preserved under `evidence/gpu-fix-20261030/`, with `REPORT.md`, host archives,
and `error-ingestion-check.json` in the GPU archive. See
[MON-001](../engineering/tech-debt.md#mon-001-terminal-native-errors) for the
remaining alerting gap and [CONTRIBUTING.md](../../CONTRIBUTING.md) for hardware
regression commands.

## Historical verification on 2026-10-22

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

Real multi-node execution and performance portability remain unverified. The
`cpu-gcc` profile was not built in the designated-host regression. CUDA failures
were exercised with masked devices; failures at every allocation, transfer, and
release operation were not individually injected.

## Blockers and risks

- CUDA toolkit support and the selected `sm_` value must match the target GPU.
  The verification used `MAKEFLAGS='-B CUDA_ARCH=sm_120'`; the profile default
  remains unchanged.
- Multi-node runs have not used a real interconnect. The two-rank MPI and
  two-PE Charm++ runs used one host. Record the two-node checksums before
  claiming cross-node performance.
- The MPI driver reads the full input on every rank. This is correct for the
  fixture but wastes I/O at scale. The roadmap keeps a split-reader as a later
  optimization.
- The Charm++ launcher differs by build. Classic Charm++ uses `charmrun +p N`.
  Reconverse builds can use `prterun -n N`. The planner supports both.

## Known operational state

The 2026-10-22 records came from macOS and a temporary Charm++ reconverse build.
That old temporary installation is not a current prerequisite. The current
master regression used isolated worktree dependencies with Open MPI 5.0.11 and
Charm++ 8.0.0. GPU validation used the isolated CUDA prefix in the 5060ti WSL
worktree. Neither run submitted a Slurm job.

## Next review

Record real two-node CPU and Charm++ checksums, cluster GPU results, and the
`cpu-gcc` build before claiming cluster acceptance. Keep the CUDA hardware
regression in the designated GPU worktree.
