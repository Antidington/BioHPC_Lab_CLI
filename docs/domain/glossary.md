# Domain Glossary

- Owner: BioHPC Lab
- Scaffold created: 2026-10-22
- Last verified: 2026-10-22

| Term | Meaning | Code mapping |
|---|---|---|
| Read | One sequencing read, stored as an id and a base string | `SeqBatch.ids`, `SeqBatch.lengths` |
| `SeqBatch` | A batch of reads in one memory layout | `native/include/bhlab/types.hpp` |
| AoS8 | Array of structures with one byte per base | `Layout::AoS8`, `layout = "aos8"` |
| SoA2 | Structure of arrays with two bits per base and 32 bases per 64-bit word | `Layout::SoA2`, `layout = "soa2"` |
| k-mer | A substring of length `k` over the DNA alphabet | `KmerCount.kmer` |
| Canonical k-mer | The smaller of a k-mer and its reverse complement | `canonical_kmer()` |
| Minimizer | The smallest canonical k-mer in a window of `w` consecutive k-mers | `Minimizer`, `compute_minimizers()` |
| `KmerShuffle` | Hash-partition local k-mers, exchange variable-length buffers, merge counts | `native/src/comm/mpi_driver.cpp` |
| Coverage | The number of times a base or k-mer appears in the reads | `KmerCount.count` |
| Signature | The fields that group comparable jobs, such as app, comm, device, layout, k, and input size bucket | `baseline.signature_from()` |
| Baseline | Median, MAD, and p95 for a metric within one signature | `baseline.build()` |
| MAD | Median absolute deviation, a robust spread measure | `baseline._stats()` |
| Alert evidence | The recent events attached to an alert | `Alert.evidence` |
| Capability | A detected runtime or library | `capabilities.Capabilities` |
| Launch plan | The resolved binary, argv, environment, and reason for a run | `planner.LaunchPlan` |
| Platform profile | A TOML file that selects the compiler and feature flags for a Makefile | `platforms/*.toml` |
| Evidence bundle | The directory written by the acceptance demo | `evidence/<timestamp>/` |
| Log event | The normalized record with time, source, job, event, level, message, and params | `logs.schema.LogEvent` |
| Slurm source | Slurm job output and `sacct` JSON records | `logs.sources.parse_slurm_line()` |
| Syslog source | Plain system log lines, including kernel OOM messages | `logs.sources.parse_text_line()` |
