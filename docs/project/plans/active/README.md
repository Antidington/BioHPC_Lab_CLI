# Active Plans

Use one plan for work with multiple dependent steps, meaningful risk, or a
need to resume across sessions. Small changes can be handled without a plan
file. Name plans descriptively, for example `YYYY-MM-DD-topic.md`.

## Plan template

```markdown
# Plan: <outcome>

- State: Proposed | Active | Blocked | Completed | Cancelled | Superseded
- Owner: TODO
- Last updated: YYYY-MM-DD
- Related requirements / ADRs: TODO

## Objective and boundaries
State the requested outcome, authorized scope, and non-goals.

## Context and decisions
Separate confirmed facts, agreed decisions, assumptions, and open questions.
Record an approval only when actually given, including its action and target.

## Acceptance criteria
Define observable success and the checks required by
[CONTRIBUTING.md](../../../../CONTRIBUTING.md) for this task.

## Steps and verification
- [ ] Step with an observable result and relevant check.

## Risks and dependencies
List only concrete risks, dependencies, and applicable approval boundaries.
Note which independent work can continue while a dependency is unresolved.

## Resume checkpoint
- Completed work and evidence: TODO
- Remaining work / blocker: TODO
- Next action: TODO
- Unrun checks and reason: TODO

## Outcome
Record results against the acceptance criteria, validation, and remaining limits.
```

Update checkpoints at meaningful changes, not after every tool call. Preserve
settled decisions; recheck volatile evidence when resuming. Move finished,
cancelled, or superseded plans to [archive](../archive/README.md), and update
links in status and roadmap. Keep unresolved follow-up work explicitly linked.
