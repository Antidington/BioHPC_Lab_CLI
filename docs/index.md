# Documentation Index

## Read by task

Use this index when you need to find context. A localized change can start in the
affected files; this is not a mandatory reading order or a completion checklist.

| Task or question | Canonical source | Owns |
|---|---|---|
| Understand or use the project | [README](../README.md) | Overview and minimal user quick start |
| Set up development or run checks | [Contributing](../CONTRIBUTING.md) | Contributor commands, validation policy, and workflow permissions |
| Find project agent rules | [Agent instructions](../AGENTS.md) | Scoped working rules and context entry points |
| Define boundaries | [Scope](product/scope.md) | Goals, non-goals, constraints, success criteria |
| Specify behavior | [Requirements](product/requirements.md) | Requirement IDs and acceptance criteria |
| Interpret domain terms | [Glossary](domain/glossary.md) | Definitions and stable code mappings |
| Understand system design | [Architecture](architecture/overview.md) | Boundaries, flows, and invariants |
| Explain a design decision | [ADRs](architecture/adr/README.md) | Decision context and consequences |
| Establish current state | [Status](project/status.md) | Verified capabilities, evidence, and blockers |
| Choose future priorities | [Roadmap](project/roadmap.md) | Now / next / later outcomes |
| Execute or resume substantial work | [Active plans](project/plans/active/README.md) | Bounded steps, decisions, and checkpoints |
| Inspect past work | [Archived plans](project/plans/archive/README.md) | Historical outcomes, not current instructions |
| Locate implementation | [Code map](engineering/code-map.md) | Non-obvious entry points, module relationships, and generated-source mappings |
| Track accepted compromises | [Technical debt](engineering/tech-debt.md) | Impact, rationale, and removal triggers |
| Operate or recover the system | [Runbook](operations/runbook.md) | Operational procedures and recovery checks |
| Learn a workflow | [Tutorials](tutorials/README.md) | Guided tasks and expected outcomes |
| Look up an interface | [Reference](reference/README.md) | Exact API, CLI, configuration, and schema contracts |
| Review released changes | [Changelog](../CHANGELOG.md) | User-visible release history |
| Report a vulnerability | [Security policy](../SECURITY.md) | Supported versions and private reporting channel |

## When to develop each document

Populate documents as the project needs them; initialization does not require
filling every template. Leave unused drafts untouched, or mark a document N/A
when its inapplicability has been established.

- Use scope and requirements when defining boundaries or behavior; use the glossary
  when domain terms need agreed definitions.
- Develop architecture and the code map when design context or implementation
  navigation needs explanation. Create an ADR for a material design decision.
- Maintain status for verified capabilities and blockers, roadmap for agreed or
  proposed priorities, and a plan for substantial work needing durable checkpoints.
- Use the debt register for concrete compromises, the runbook for operational
  workflows, tutorials for guided tasks, and reference for exact interface contracts.
- Keep release history when releasing; establish the security reporting channel
  before publishing. The relevant root documents own contributor and user setup.

## Maintenance and evidence

Read and update only the sources affected by the task. Each fact or command
has one canonical home; link to it from other documents. The code map points
to implementation while architecture explains design; status reports what
works while roadmap proposes what comes next and plans describe execution.

Generated documents are drafts. TODOs and example IDs are not requirements,
accepted decisions, completed checks, or known defects. Fill relevant sections
as evidence becomes available; mark inapplicable sections with a reason.
A creation date is not a verification date. Set "Last verified" only after
checking the content against code, configuration, tests, or agreed decisions,
and link supporting evidence for claims about current behavior.

Ordinary docs provide task context; scoped working instructions belong in
AGENTS.md. Add a nested AGENTS.md only for a real directory-specific rule.
Do not turn every documentation page into an automatically loaded instruction
file. Preserve settled user decisions and distinguish proposals from approval.
