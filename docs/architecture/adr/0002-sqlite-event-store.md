# 0002. Use SQLite plus JSONL for events and alerts

- Status: Accepted
- Date: 2026-10-22

## Context

The anomaly detector needs to ingest three log sources, filter by time and job,
extract keywords, and attach preceding events to an alert. A log platform such
as Elasticsearch or Kafka would add services, credentials, and operational work
that the acceptance does not need.

## Decision

Normalize events into one SQLite table with indexes on job, source, and event.
Keep `alerts.jsonl` as an append-only external record and export events as JSONL
on demand. The watcher holds a per-job ring buffer in memory for evidence.

## Consequences

- The whole store is one file that a reviewer can copy into an evidence bundle.
- Queries use SQL, and keyword extraction runs in Python over a bounded result
  set. The demo scale fits comfortably.
- SQLite is not a distributed store. It is not suitable for many concurrent
  writers or multi-tenant ingestion. That is outside the project scope.
- The schema is the contract. Changing it requires a migration and an update to
  the log schema reference.
