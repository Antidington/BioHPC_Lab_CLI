# 0001. Use one kernel core with thin communication and device drivers

- Status: Accepted
- Date: 2026-10-22

## Context

The project needs MPI and Charm++, CPU and GPU, and two memory layouts without
building two copies of the bioinformatics software. The acceptance budget is one
month. A full framework or a portable parallel abstraction such as Kokkos would
add build and debugging cost before the first demo.

## Decision

Keep the algorithm in `native/src/kmer.cpp` and `native/src/minimizer.cpp` behind
the `SeqBatch` type. Put communication in `native/src/comm/` and device code in
`native/src/device/`. The MPI driver implements `KmerShuffle` with
`MPI_Alltoallv` and `MPI_Gatherv`. The Charm++ driver uses an array of chares and
a concatenating reduction. The GPU driver emits canonical k-mers and reduces
them with Thrust.

The Python planner selects a backend by configuration. The core never reads
`--comm` or `--device`.

## Consequences

- One correctness test covers all backends because they share the core and the
  output format.
- The MPI path was verified on two ranks. The Charm++ path was verified on two
  PEs with a reconverse build and `prterun`. The CUDA path compiles only on a
  host with `nvcc`, so its acceptance evidence is still pending.
- Each new backend is a thin adapter, not a new application. The cost is that
  the Charm++ driver duplicates a small amount of chare setup in its template.
- The design gives up single-source portability. That is acceptable because the
  indicator asks for one software with performance portability, not one source
  file for every device.
