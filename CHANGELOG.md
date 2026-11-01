# Changelog

## 0.1.1

### Fixed

- Fix `gpu-cuda` header inclusion and dependency tracking in generated Makefiles.
- Propagate CUDA runtime failures through the native error path and add masked-device regression coverage.

### Planned

- Add MPI node configuration and cross-node regressions, including fixes to native and generated drivers.
- Add Charm++ node-list configuration and cross-node regressions, including launcher and generated-driver fixes.
- Extend `gpu-cuda` hardware regressions and representative CPU/GPU benchmarks; fix issues identified during validation.

## 0.1.0

- Add the `bhlab` CLI with init, doctor, dependency probe, build, codegen, run,
  bench, log, baseline, watch, alert, and demo commands.
- Add the C++17 k-mer and minimizer core with `aos8` and `soa2` layouts.
- Add the MPI and Charm++ drivers with a hash-partitioned k-mer shuffle and
  serial comparison.
- Add local CPU, MPI, and Charm++ code generation. All three generated drivers
  are verified, including a two-PE Charm++ run through `prterun`.
- Add generated Makefiles for local, MPI, CPU GCC, and CUDA profiles.
- Add SQLite log normalization for application, Slurm, and syslog sources.
- Add robust baselines, keyword rules, baseline deviation, exit code, silence,
  and retry rules.
- Add fault replay, alert evidence, and the acceptance demo.
