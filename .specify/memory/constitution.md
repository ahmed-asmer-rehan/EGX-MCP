<!--
Sync Impact Report
- Version change: 1.0.0 → 1.1.0
- Modified principles: n/a (no Core Principle renamed/redefined)
- Modified sections:
  - Agent Integration Constraints: supported agent hosts narrowed from "Claude Desktop, Claude
    Cowork, Claude Code" to "Claude Cowork, Claude Code" — Claude Desktop (chat) dropped as a
    target host per explicit user decision during `/speckit-analyze` remediation on
    specs/001-egx-cli; the invocation mechanism for the remaining two hosts is now stated as
    confirmed (Skill-driven local execution) rather than an open question, resolving the
    constitution-alignment finding raised by that analysis (a HIGH-severity mismatch between this
    document asserting subprocess invocation as settled fact and the plan/research flagging it as
    unverified for 2 of 3 hosts)
  - Principle I rationale: example host list updated to match (Claude Cowork, Claude Code)
- Added sections: none
- Removed sections: none
- Rationale for MINOR bump: this changes the meaning of a normative constraint (which hosts this
  project targets and on what basis), which is more than a wording clarification (PATCH) but does
  not remove or redefine a Core Principle (MAJOR)
- Templates requiring updates:
  - ✅ .specify/templates/plan-template.md (no changes needed)
  - ✅ .specify/templates/spec-template.md (no changes needed)
  - ✅ .specify/templates/tasks-template.md (no changes needed)
  - ✅ specs/001-egx-cli/{spec,plan,research,tasks}.md and contracts/cli-contract.md (updated in
    the same change to drop Claude Desktop and reflect the confirmed invocation mechanism)
  - ⚠ README.md (still describes the MCP server as the integration surface; update when CLI ships — tracked as follow-up, not a blocker for spec/plan/tasks)
- Follow-up TODOs: none
-->

# EGX-CLI Constitution

## Core Principles

### I. CLI-First, Agent-Consumable
Every capability MUST be exposed as a subcommand of a single CLI entry point, not as a library
API alone. Default output MUST be terse, parseable text (plain text or a compact table) sized
for LLM context economy; a `--json` flag MUST be available on every data-returning command for
structured consumption. Commands MUST write results to stdout and errors/diagnostics to stderr,
and MUST return meaningful process exit codes (0 success, non-zero on failure) so a calling agent
can branch on outcome without parsing prose.
Rationale: the CLI's primary consumer is an AI agent (Claude Cowork, Claude Code) invoking it as
a subprocess, not a human at an interactive shell — output shape is a functional requirement, not
polish.

### II. Cross-Platform Parity
The tool MUST run identically on Linux (Ubuntu, Fedora) and Windows 10+. No command may depend on
a platform-specific code path (shell syntax, path separators, process/signal handling) without a
tested equivalent on the other platform. Packaging/installation MUST use a method that works
unmodified on both target families (e.g. `uv`/`pipx`), never a bash-only or PowerShell-only
install script as the sole path.
Rationale: the tool must be installable and runnable by agents operating on either OS without
per-platform forks or documentation branches.

### III. Bounded, Resilient Data Fetching (NON-NEGOTIABLE)
Every fetch function MUST use bounded, fast-fail retries (reference: ≤3 tries, ≤0.3s delay) —
never the unbounded/slow retry policy that previously caused MCP timeout errors (`-32001`).
Multi-ticker operations MUST fetch independent tickers in parallel, never sequentially in a loop.
Every long-running command MUST complete or fail within a documented time budget; a command that
cannot meet its budget MUST fail fast with a clear error rather than hang.
Rationale: directly codifies the lesson from the intraday-timeout production incident (20
tries/0.5s delay, sequential fetch across ~100 tickers) that this CLI replaces the MCP server to
fix — regressing on this principle reintroduces the exact bug this project exists to resolve.

### IV. Concise Agent-Facing Responses
Default responses MUST stay short and information-dense: large result sets (e.g. risers-over-time
across ~100 tickers) MUST be summarized, paginated, or capped by default, with an explicit flag to
request the full/verbose result. Stack traces, retry-attempt logs, and other internal noise MUST
NOT reach stdout/the default response; verbose/debug output is opt-in only (e.g. `--verbose`).
Rationale: every token an agent reads to interpret output is context spent — verbosity is a cost,
not a courtesy.

### V. Reuse Over Rewrite
The CLI is a thin adapter over the existing `Domain/` business logic (`egx_controller`,
`download`, `gold_controller`, `date_parser`). Business logic changes belong in `Domain/`; CLI
command handlers MUST NOT duplicate or fork logic that already exists there. New Domain logic
introduced for the CLI MUST remain free of any MCP/CLI-specific concerns so it stays reusable.
Rationale: the CLI and the prior MCP server are two transports over the same domain — duplicating
logic between them guarantees drift and double maintenance.

### VI. Skill-Documented Interface
Every command MUST ship with accurate guidance in the companion Claude Skill (`SKILL.md`)
describing when to invoke it, its arguments, and how to interpret its output. The skill
documentation MUST be updated in the same change that adds, removes, or alters a command's
interface — it is not a follow-up task.
Rationale: an agent's only "onboarding" to this tool is the skill file; stale skill docs make the
CLI effectively undiscoverable to the agents it's built for, regardless of how well the CLI itself
works.

## Agent Integration Constraints

- Supported agent hosts: Claude Cowork and Claude Code, each invoking the CLI as a subprocess (not
  over MCP stdio) — Claude Code via its Bash tool, Claude Cowork via a Skill capable of local code
  execution. Claude Desktop (chat) is explicitly out of scope for this CLI; it continues to reach
  EGX data only through the existing MCP server.
- No test suite currently exists; manual/CLI-invocation verification is acceptable in its place,
  but every new or changed command MUST be spot-checked on both Linux and Windows before being
  considered done — parity is validated by running the command, not assumed from the code.
- No unnecessary abstractions: prefer direct, readable command handlers over frameworks or layers
  the current scope doesn't need (YAGNI). A bug fix or single new subcommand does not justify a
  plugin system, config DSL, or similar.

## Development Workflow

- Each feature/change proceeds through the spec-kit flow: `/speckit-specify` → (optional
  `/speckit-clarify`) → `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`, gated by this
  constitution's principles at the plan stage.
- Any deviation from a principle above (e.g. an unavoidable platform-specific path, a necessarily
  sequential fetch) MUST be called out explicitly in the plan's Complexity/justification section
  with a concrete reason — silent deviation is not permitted.
- Command interface changes and their corresponding `SKILL.md` updates MUST land in the same
  change (see Principle VI).

## Governance

This constitution supersedes ad hoc practice for this project. Amendments are made via
`/speckit-constitution`, which MUST: record the version bump (MAJOR for backward-incompatible
principle removal/redefinition, MINOR for new/materially expanded principles or sections, PATCH
for clarifications/wording), update the Sync Impact Report, and propagate changes to dependent
templates. All plans MUST include a Constitution Check gate verifying compliance before Phase 0
research begins, and again after Phase 1 design. Complexity that violates a principle MUST be
justified in the plan, not silently introduced. Use `CLAUDE.md` at the repo root for day-to-day
runtime/architecture guidance that supplements (never contradicts) this document.

**Version**: 1.1.0 | **Ratified**: 2026-09-04 | **Last Amended**: 2026-09-05
