# 0004. Generate Makefiles instead of adding a second build system

- Status: Accepted
- Date: 2026-10-22

## Context

The indicator requires generated Makefiles for at least two platforms. The
native code is small, and the project already needs to probe compilers and
libraries. A CMake build would be convenient, but it would create two build
paths and one more thing to keep in sync.

## Decision

Generate `build/Makefile.<platform>` and `build/config.<platform>.mk` from a
platform TOML and the capability report. The Makefile compiles the local core,
the MPI binary when MPI is present, and the Charm++ binary only when the user
asks for `--with-charm`. Each platform has a separate object directory and
config file.

## Consequences

- The generated Makefile is the build artifact the acceptance can inspect.
- Header dependencies use `-MMD -MP`, so a changed `PipelineSpec` rebuilds the
  objects that include it.
- The Makefile is less capable than CMake for cross-compilation and packaging.
  The project does not need those features.
- A new platform is a TOML profile plus the capability probe. No Python build
  logic changes.
