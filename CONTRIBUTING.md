# Contributing

## Development setup

This is the canonical guide to contributor commands and checks. Keep end-user
usage in [README.md](README.md). Obtain commands from manifests, scripts, and CI;
link their definitions so this guide stays consistent with executable configuration.

TODO: Add supported runtimes, prerequisites, and environment setup.

| Purpose | Command / definition | Working directory / prerequisites | Evidence / last verified |
|---|---|---|---|
| Setup | TODO | TODO | Not verified |
| Focused tests | TODO | TODO | Not verified |
| Full tests | TODO | TODO | Not verified |
| Lint / format check | TODO | TODO | Not verified |
| Build | TODO | TODO | Not verified |

TODOs are not executable commands. Mark an inapplicable check N/A with a reason.

## Validation policy

TODO: Map actual change types to required checks and observable pass conditions.
Include broader checks only where risk or CI policy requires them. For documentation
changes, check affected commands, examples, or links as applicable.

| Change type / trigger | Required check (from above) | Pass condition |
|---|---|---|
| TODO | TODO | TODO |

After applicable checks pass, stop unless a new edit, failure, or unresolved concern
requires more checking. Record unavailable environments and unrun checks in the task
result; documentation of a command is not evidence that it passed.

## Workflow permissions and effects

TODO: Document only established project-specific permissions for workflows that
need them. For each, identify the command, environment, targets, data or network
effects, allowed repair/retry actions, and any approval boundary with its source.
Record verified isolation separately from authorization; local execution alone
does not establish either. An unfinished section does not revoke existing user
authorization or require approval for ordinary in-scope work.

Keep deployment and recovery procedures in the [runbook](docs/operations/runbook.md).

## Making changes

TODO: Add repository-specific branch, commit, and review expectations.

## Pull requests

Describe the problem, resulting behavior, validation performed, and remaining risk
or follow-up work.
