# Project Agent Instructions

## Project constraints

Record repository-specific invariants and exceptions here when established.
Keep team-required rules self-contained; do not assume contributors share personal
global instructions. Add nested AGENTS.md files only for directory-specific rules.

## Context by task

- For a small, localized change, inspect the affected files directly. Use the
  [documentation index](docs/index.md) when you need to locate relevant context.
- For development commands and applicable checks, use
  [CONTRIBUTING.md](CONTRIBUTING.md). Discover missing details from manifests,
  scripts, and CI; unfinished documentation alone does not block authorized work.
- For design changes, use the [architecture overview](docs/architecture/overview.md).
  For substantial work that needs a saved plan, use the
  [active plans](docs/project/plans/active/README.md) and latest relevant checkpoint.
- Drafts, TODOs, and archived plans are context, not verified behavior or approval.

## Workflow boundaries

Project-specific workflow permissions belong with the commands in
[CONTRIBUTING.md](CONTRIBUTING.md). Record the operation, environment, affected
targets, and permitted effects only after they are established. This scaffold
does not establish that tests are isolated or authorize external writes.

## Repository invariants

- Same input, app, and `k` must produce the same output checksum across `aos8`
  and `soa2`, and across local and MPI. Add or update a test when that can break.
- Every run path emits the `LogEvent` schema. The schema is documented in
  `docs/reference/log-schema.md`.
- Backend selection lives only in `src/bhlab/planner.py`. Do not branch on
  communication or device inside commands.
- The tool never submits Slurm jobs. It may write a script with `--emit-slurm`
  and read Slurm logs.
- Do not add a scheduler, a web console, a custom MPI runtime, or a machine
  learning model. The scope document owns the exclusions.
- The generated Makefile is the build contract. A new platform is a TOML profile,
  not a second build system.

## Completion

For implementation, continue within the authorized scope through applicable checks,
fixes for problems introduced by the change, and relevant rechecks. Stop when the
acceptance criteria and required checks are satisfied, or report a concrete blocker
or necessary approval; continue independent authorized work where possible.
Preserve unrelated work, review the final diff, and update canonical docs affected
by the change. Report results and any unrun checks without claiming unverified success.
