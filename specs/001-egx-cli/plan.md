# Implementation Plan: EGX CLI Tool

**Branch**: `bug-interaday-timeout` | **Date**: 2026-09-04 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-egx-cli/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Add a new, agent-invocable CLI (`egx`) that exposes the existing EGX stock and gold-price
capabilities — currently reachable only via the EGX-MCP stdio server — as cross-platform
subcommands, so Claude Cowork and Claude Code can call it directly as a subprocess. The CLI is a
thin adapter over the existing `Domain/` layer, whose fetch functions already (on this branch) use
bounded retries and parallel multi-ticker fetching (with one correctness gap fixed as part of this
feature — see research.md R3 addendum); the CLI adds an outer per-command time budget on top of
that, concise default text output with a `--json` escape hatch, and a companion Claude Skill
document so an agent knows which subcommand answers which question. This CLI becomes the primary
integration surface going forward (spec Assumptions) for these two hosts; `server.py`/MCP is left
in place, unmodified, and marked deprecated for them — its removal is separate future cleanup, not
part of this feature. Claude Desktop (chat) is out of scope for this CLI and keeps using the MCP
server exclusively (decided during `/speckit-analyze` remediation, resolving that analysis's C1
finding). Both remaining hosts have a confirmed invocation mechanism (research.md R6): Claude Code
via its Bash tool, Claude Cowork via a Skill capable of local code execution.

## Technical Context

**Language/Version**: Python 3.14 (matches existing `pyproject.toml` `requires-python`)
**Primary Dependencies**: `Typer` (Click-based CLI framework, plain-text mode — no `rich` markup in default output, to keep it agent-parseable) added to `pyproject.toml`; reuses existing `Domain/` dependencies (`pandas`, `holidays`, `tvDatafeed`, `retry`, `bs4`/`httpx`) unchanged
**Storage**: N/A — stateless, read-only pass-through to the existing market/gold data sources
**Testing**: No formal automated test suite is introduced by this feature (matching the project's
existing state and the constitution's explicit allowance for manual/CLI-invocation verification);
verification is via the cross-platform spot-checks and `quickstart.md` walkthrough in tasks.md's
Polish phase. `typer.testing.CliRunner` remains a natural fit if/when a test suite is added later,
but is not built here — this line is intentionally consistent with tasks.md generating no test
tasks.
**Target Platform**: Linux (Ubuntu, Fedora) and Windows 10+, installed as a console-script entry point via `uv tool install` / `pipx install` (both generate the correct platform shim — `.exe` on Windows)
**Project Type**: Single project — new `egx_cli/` package added alongside the existing `Domain/` and `server.py`; no split frontend/backend or mobile target
**Performance Goals**: Single-ticker commands (live price, last price) respond within 10s p99 (spec SC-001); market-wide riser commands respond within 30s p95 across the ~100-ticker universe (spec SC-002)
**Constraints**: No new external market-data source; no redesign of `Domain/` fetch algorithms —
only the minimal, targeted additions/fixes documented in research.md (the FR-003 name-lookup
helper, the `getLivePrice` fallback-to-last-close fix needed to make FR-001 actually true, and the
`as_completed` partial-results fix needed to make Principle III/SC-002 actually true); default
output must stay concise per Constitution Principle IV; must not leave the process hanging past
its documented budget even on partial network failure
**Scale/Scope**: ~100 covered EGX tickers (existing `egx_controller` company dict), 8 subcommands (live price, last price, company directory/lookup, price-range history, intraday history, period risers, intraday risers, gold price)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | How this plan satisfies it |
|---|---|---|
| I. CLI-First, Agent-Consumable | PASS | Typer subcommands per capability; global `--json` flag on every data command; results on stdout, errors on stderr, non-zero exit on failure (contracts/cli-contract.md) |
| II. Cross-Platform Parity | PASS | Pure-Python package, no shell/OS-specific code paths, `pathlib` throughout, installed via `uv`/`pipx` console-script entry point which both platforms support natively; Phase 2 tasks include a spot-check pass on Linux and Windows |
| III. Bounded, Resilient Data Fetching (NON-NEGOTIABLE) | PASS | `Domain/download.py` on this branch already retries with `tries=3, delay=0.3` and fetches multi-ticker requests in parallel via `ThreadPoolExecutor`; its 25s `as_completed` timeout currently discards already-completed results on timeout, undermining this principle for large fan-outs — fixed as a Foundational-phase task (research.md R3 addendum) to keep partial results instead. The CLI additionally adds its own outer per-command budget (10s single-ticker / 30s market-wide, research.md R3) so a command fails fast and cleanly regardless |
| IV. Concise Agent-Facing Responses | PASS | Default text output is one value or one small table per command; riser commands default to ticker + latest value + % change only (full series gated behind `--json`); no tracebacks/retry logs reach stdout (contracts/cli-contract.md) |
| V. Reuse Over Rewrite | PASS | CLI command handlers call `EGXController`/`GoldController` methods directly; the only new/changed `Domain/` code is the FR-003 company-name-search helper, the FR-001 `getLivePrice` fallback fix, and the R3 `as_completed` fix — all genuine business-logic corrections, not CLI-specific duplication |
| VI. Skill-Documented Interface | PASS | `.claude/skills/egx-cli/SKILL.md` (research.md R7) is a first-class Phase-1/Phase-2 deliverable, authored from the same command contracts as the CLI itself, and its update is required in the same change as any command-interface change (see Development Workflow in constitution) |

No violations requiring Complexity Tracking.

*Re-checked after Phase 1 design*: the table above reflects the state after Phase 0 research and
Phase 1 design artifacts (research.md, data-model.md, contracts/cli-contract.md, quickstart.md)
were produced — it incorporates decisions only settled during research (the R3 `download.py` fix,
the R7 skill-path correction, R6's host-invocation resolution) and remains PASS on all six
principles with no new violations introduced by the Phase 1 design. This satisfies the
constitution's Governance requirement for a post-Phase-1 re-check (raised as finding C2 in this
feature's `/speckit-analyze` pass).

## Project Structure

### Documentation (this feature)

```text
specs/001-egx-cli/
├── plan.md              # This file (/speckit-plan command output)
├── research.md           # Phase 0 output (/speckit-plan command)
├── data-model.md          # Phase 1 output (/speckit-plan command)
├── quickstart.md          # Phase 1 output (/speckit-plan command)
├── contracts/             # Phase 1 output (/speckit-plan command)
│   └── cli-contract.md
└── tasks.md               # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
egx_cli/                          # NEW — the CLI adapter package
├── __init__.py
├── __main__.py                   # `python -m egx_cli` entry point
├── app.py                        # Typer() app instance; registers all subcommands; --json/--verbose globals
├── commands/
│   ├── __init__.py
│   ├── price.py                  # `egx price last <ticker>`, `egx price live <ticker>`
│   ├── companies.py              # `egx companies list`, `egx companies find <name>`
│   ├── history.py                # `egx history range <ticker> <start> <end>`, `egx history intraday <ticker> <date>`
│   ├── risers.py                 # `egx risers period <start> <end> [-n N]`, `egx risers intraday [-n N]`
│   └── gold.py                   # `egx gold`
├── output.py                     # shared text/JSON renderers, exit-code constants
└── timing.py                     # per-command time-budget guard (research.md R3)

Domain/                            # EXISTING — reused, with three targeted fixes across two files
├── egx_controller.py              # + `findTicker(name)` helper (FR-003, R1) + getLivePrice fallback-to-last-close fix (FR-001, see plan Constraints)
├── download.py                    # + as_completed partial-results fix only (R3 addendum) — parallel/bounded-retry structure unchanged
├── gold_controller.py             # unchanged
└── date_parser.py                 # unchanged

.claude/
└── skills/
    └── egx-cli/
        └── SKILL.md                # NEW — companion Claude Skill (FR-014), path chosen for Claude Code auto-discovery (research.md R7); also the confirmed mechanism Claude Cowork uses to learn CLI invocation (research.md R6)

server.py                          # EXISTING — untouched; deprecated per spec Assumptions, not removed by this feature
pyproject.toml                     # + `typer` dependency, + `[project.scripts] egx = "egx_cli.app:main"`
```

**Structure Decision**: Single-project layout (Option 1). The CLI is added as a new top-level
`egx_cli/` package that imports from the existing `Domain/` package — it does not nest under
`src/` since the repository already uses a flat top-level-package layout (`Domain/`, `server.py`).
`server.py`/MCP is left in place unmodified and marked deprecated in docs (spec Assumptions);
this feature is purely additive at the source-tree level, plus the two narrowly-scoped `Domain/`
fixes called out above.

## Complexity Tracking

*No Constitution Check violations — this section is intentionally empty.*
