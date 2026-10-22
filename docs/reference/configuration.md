# Configuration Reference

## `bhlab.toml`

`bhlab init` writes the default file. All keys are optional.

```toml
[comm]
order = ["mpi", "charm", "local"]

[device]
order = ["gpu", "cpu"]

[layout]
map = { gpu = "soa2", cpu = "aos8" }

[paths]
build = "build"
runs = "runs"
db = "var/events.db"
evidence = "evidence"

[bench]
repeat = 3
platform = "local-clang"

[anomaly]
min_samples = 8
window = 50
dedupe_seconds = 300
webhook = ""
```

| Section | Key | Meaning |
|---|---|---|
| `comm` | `order` | Auto selection order. The first detected backend wins |
| `device` | `order` | Auto selection order. `gpu` is skipped when CUDA is absent |
| `layout` | `map` | Default layout for a device |
| `paths` | `build`, `runs`, `db`, `evidence` | Relative to the project root |
| `bench` | `repeat`, `platform` | Default benchmark repetitions and build profile |
| `anomaly` | `min_samples` | Minimum normal jobs before a baseline can alert |
| `anomaly` | `window` | Events kept per job for alert evidence |
| `anomaly` | `dedupe_seconds` | Suppress the same rule for the same job within this window |
| `anomaly` | `webhook` | Optional HTTP endpoint for JSON POST alerts |

## Platform profiles

Profiles live in `platforms/`. Each profile is a TOML file with these keys.

| Key | Meaning |
|---|---|
| `name` | Profile name, used in artifact paths |
| `cxx` | Host C++ compiler |
| `mpicxx` | MPI compiler wrapper |
| `charmc` | Charm++ compiler wrapper |
| `nvcc` | CUDA compiler |
| `cxxflags` | Host compile flags |
| `ldflags` | Link flags |
| `cuda_arch` | CUDA architecture, for example `sm_80` |
| `openmp`, `mpi`, `charm`, `cuda` | Feature gates combined with the capability probe |

`local-clang`, `mpi-clang`, and `charm-clang` are development profiles.
`cpu-gcc` and `gpu-cuda` are the acceptance profiles. A profile never installs a
tool. It selects flags for tools the probe found.

## Auto selection

The planner resolves a run in this order.

1. Communication. An explicit `--comm` must be available. `auto` walks
   `comm.order` and picks the first available backend.
2. Device. An explicit `--device gpu` requires CUDA. `auto` walks
   `device.order` and skips `gpu` when CUDA is absent.
3. Layout. An explicit `--layout` is kept. `auto` reads `layout.map[device]`.

The resolved reason is printed by `--dry-run` and stored in `run.json`.

## Files written by the tool

| Path | Writer |
|---|---|
| `build/Makefile.<platform>` | `bhlab build` |
| `build/config.<platform>.mk` | `bhlab build` |
| `build/gen/*.cpp`, `build/gen/*.ci` | `bhlab codegen` |
| `runs/<job>/events.jsonl` | Native app |
| `runs/<job>/run.json` | `bhlab run` |
| `alerts.jsonl` | `bhlab watch` |
| `evidence/<timestamp>/` | `bhlab demo acceptance` |
