# 0003. Use a line-based pipeline DSL and templates

- Status: Accepted
- Date: 2026-10-22

## Context

The indicator asks for at least two domain communication keywords that generate
executable code. A general DSL with a grammar, type checker, and optimizer would
take longer than the rest of the tool.

## Decision

Parse a small pipeline file line by line. Accept `pipeline`, `input`,
`scatter_reads`, `shuffle_kmers`, and `gather_stats`. Render C++ drivers with
Jinja2 for local, MPI, and Charm++ targets. The generated driver calls the same
public framework as the hand-written app.

## Consequences

- The parser is under 100 lines and fails with a named error on an unknown
  keyword.
- The generated local, MPI, and Charm++ drivers all compile and match the
  hand-written checksum on the development host.
- The DSL cannot express arbitrary control flow. That is deliberate. Adding a
  keyword means adding a parser entry, a template hook, and a test.
