# Technical Debt

- Owner: BioHPC Lab
- Scaffold created: 2026-10-22
- Last verified: 2026-10-22; MON-001 recorded 2026-11-01

| Item | Impact | Rationale | Removal trigger |
|---|---|---|---|
| Reads with bases outside A, C, G, T are skipped | Valid reads with `N` are silently dropped | Keeps both layouts correct without an N mask | A reviewer needs N-aware k-mers |
| MPI ranks read the full input | I/O is duplicated per rank | Simplest correct distributed path | A real multi-node run shows I/O as the bottleneck |
| `KmerShuffle` sends all local k-mers to all owners | Memory grows with the local k-mer set | Clear implementation of the common algorithm | A larger read set exceeds rank memory |
| CUDA emits every k-mer, then sorts | GPU memory and time scale with total k-mers | Correct first GPU path | GPU numbers are needed for acceptance |
| Charm++ codegen duplicates chare setup | Two places to fix a Charm++ API change | Keeps the generated driver standalone | The generated and framework drivers diverge |
| Charm++ launcher varies by build | `charmrun` and `prterun` need different flags | The planner detects both | A site uses a third launcher |
| Slurm parser handles a small set of messages | Some cluster errors become generic `slurm_log` | Fixtures cover the demo cases | A real job produces an unrecognized failure |
| Watcher polls files, no inotify | Up to one interval of latency | Works on NFS and needs no extra daemon | Sub-second latency is required |
| `duration_per_gb` explodes for tiny inputs | Baseline values look large in demos | Keeps one metric across input sizes | Baselines are compared across very different file sizes |
| Benchmark runs are short | Throughput numbers are functional, not performance claims | The local host is a laptop | The cluster matrix is recorded |
| Charm++ readonly paths are fixed at 4096 bytes | Very long paths are truncated | Keeps readonly broadcast simple | A real path exceeds the buffer |

## MON-001 Terminal native errors

- Status: Open, observed 2026-11-01.
- Impact: An error-only native stream is stored but raises no default `exit`
  alert. The live watcher also does not mark an `error` event as an ended job,
  so terminal-error handling must be considered when reviewing silence alerts.
- Cause: Native exceptions emit `error` with `exit_code=1`; the exit-code rule
  and watcher completion tracking require `run_end`.
- Evidence: `evidence/gpu-fix-20261030/` retains the masked-device events, raw
  61/62 GPU result, independent contract review, and read-only ingestion check.
- Resolution scope: Define a terminal-error event contract and verify alert
  deduplication and live watcher completion. The CUDA repair preserves the
  existing event contract and does not change the shared alert engine.
