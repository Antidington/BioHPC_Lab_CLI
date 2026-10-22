# Pipeline DSL

The pipeline file is line based. A line is `keyword` followed by optional
`key=value` pairs. `#` starts a comment.

## Example

```
pipeline kmer_qc {
  input "fixtures/reads/tiny.fq"
  scatter_reads chunk=1000000
  shuffle_kmers key=canonical
  gather_stats
}
```

## Keywords

| Keyword | Class | Meaning | Generated call |
|---|---|---|---|
| `scatter_reads` | Domain communication | Distribute reads across ranks or chares | `Step::ScatterReads` equivalent |
| `shuffle_kmers` | Domain communication | Hash-partition and exchange k-mer counts | `bhlab::KmerShuffle` path |
| `gather_stats` | Collective | Collect summary counts for output | MPI gather or Charm++ reduction |

A pipeline needs at least two keywords. Unknown keywords fail with a named
error. The generated driver receives the keyword list in `PipelineSpec.steps`,
so the run event records which steps ran.

## Targets

| `--comm` | Output | Runtime |
|---|---|---|
| `local` | `<name>_local.cpp` | Direct execution |
| `mpi` | `<name>_mpi.cpp` | `mpirun` |
| `charm` | `<name>_charm.cpp` and `<name>_charm.ci` | `charmrun` |

Generated code calls the same public headers as the hand-written apps. It does
not copy the algorithm.

## Build and run

```sh
bhlab codegen pipelines/kmer_qc.bhl --comm local
bhlab build --platform local-clang
./build/bin/kmer_qc --input fixtures/reads/tiny.fq \
  --output runs/generated/counts.tsv --events runs/generated/events.jsonl \
  --k 15 --layout aos8
```

The generated local binary is named after the pipeline, without the `_local`
suffix. The MPI binary keeps the `_mpi` suffix.

## Limits

- No variables, loops, or conditionals.
- No type checking beyond the keyword list.
- The pipeline input path is documentation. The runtime input comes from
  `--input`.
- The Charm++ template is not compiled on the development host. Verify it on a
  host with `charmc`.
