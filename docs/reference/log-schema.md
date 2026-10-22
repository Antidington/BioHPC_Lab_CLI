# Log Schema

The canonical event is one JSON object per line. SQLite stores the same fields,
with `params` as a JSON string.

## Fields

| Field | Type | Required | Meaning |
|---|---|---|---|
| `ts` | string | yes | ISO 8601 timestamp, UTC preferred, for example `2026-10-22T10:00:00Z` |
| `source` | string | yes | `app`, `slurm`, `syslog`, or `text` |
| `job_id` | string | yes | Job or run identifier |
| `host` | string | yes | Host name, `slurm`, or `unknown` |
| `event` | string | yes | Event name, for example `run_start` |
| `level` | string | yes | `info`, `warning`, or `error` |
| `message` | string | no | Human-readable detail |
| `params` | object | no | Structured key-value data |

## Example

```json
{"ts":"2026-10-22T10:00:03Z","source":"app","job_id":"fault-001","host":"node01","event":"error","level":"error","message":"CUDA out of memory while allocating k-mer table","params":{"code":"OOM","exit_code":"137"}}
```

## Application events

| Event | Written when | Useful params |
|---|---|---|
| `run_start` | Before loading reads | app, comm, device, layout, input_bytes, k, ranks |
| `pipeline` | A generated driver starts | steps |
| `phase_end` | Counting or sketching finishes | phase, seconds, kmers, reads, skipped_reads |
| `shuffle_end` | MPI or Charm++ exchange finishes | phase, messages, bytes, kmers |
| `verify` | `--verify-shuffle` compares to serial | match |
| `run_end` | The run finishes | exit_code, duration_s, peak_rss_mb, output |
| `error` | The run fails | exit_code, code, duration_s |

## Source adapters

- `app` reads JSONL. A line that is not JSON becomes an `app_log` event with the
  line as its message.
- `slurm` reads timestamped text and `sacct --json` records. It recognizes OOM,
  memory limit, cancelled, and generic error lines.
- `syslog` and `text` read syslog-style or ISO-prefixed lines. Kernel OOM lines
  become `oom_kill`.

## Level inference

A line that contains `oom`, `out of memory`, `killed`, `fatal`, `abort`, `error`,
or `failed` becomes `error`. A line that contains `warn` becomes `warning`.
Everything else is `info`.

## Storage

`events` has a unique key on the timestamp, source, job, event, message, and
params. Re-normalizing the same file does not duplicate rows. Indexes cover
`(job_id, ts)`, `source`, and `event`.

`alerts` stores the rule, severity, message, and an evidence array of event
objects. The watcher also appends each alert to `alerts.jsonl` next to the
database.
