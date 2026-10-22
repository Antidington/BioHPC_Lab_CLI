# Active Plans

## Cluster verification for CUDA and multi-node runs

- Status: Active
- Owner: BioHPC Lab
- Created: 2026-10-22

The local CPU, two-rank MPI, and two-PE Charm++ paths are verified. This plan
closes the remaining CUDA and multi-node gaps. It is not an implementation plan
for new features.

### Steps

1. Load the site modules for GCC, Open MPI, Charm++, CUDA, zlib, libdeflate,
   bzip2, lzma, and htslib. Run `bhlab doctor` and save the JSON output.
2. Build `cpu-gcc` on a CPU login node. Record the generated Makefile and
   `config.cpu-gcc.mk`.
3. Run the k-mer app on two nodes with `mpirun`. Use `--verify-shuffle` and
   compare the SHA-256 to a single-rank run. Save `bench.csv` and the events.
4. Build `gpu-cuda` on a GPU node. Set `cuda_arch` in
   `platforms/gpu-cuda.toml` to the device capability. Run the same input with
   `--device gpu --layout soa2`. Compare the checksum to the CPU run.
5. Run the local Charm++ checksum on the cluster. The local build already
   passes with two PEs, so this step confirms the cluster launcher and runtime.
6. Run `bhlab demo acceptance --full` and archive `evidence/<timestamp>/`.
7. Update `docs/project/status.md` with the commands, checksums, and any
   remaining gaps.

### Evidence to keep

- `doctor --json`
- `Makefile.cpu-gcc`, `config.cpu-gcc.mk`
- `Makefile.gpu-cuda`, `config.gpu-cuda.mk`
- `bench.csv` and `manifest.json`
- MPI and Charm++ event logs with `verify.match=1`
- The GPU checksum comparison
- The final `SUMMARY.md`

### Stop condition

Stop when the status page has one verified row for two-node CPU, GPU, and
Charm++, or when a cluster limitation is recorded with the exact failing command
and error.
