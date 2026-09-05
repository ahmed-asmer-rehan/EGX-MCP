# Tasks: EGX CLI Tool

**Input**: Design documents from `/specs/001-egx-cli/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli-contract.md, quickstart.md

**Tests**: Not explicitly requested in the spec, so no dedicated test-writing tasks are generated
(per Task Generation Rules). Verification instead happens via the manual spot-check and
quickstart-validation tasks in the Polish phase, consistent with the constitution's allowance for
manual/CLI-invocation testing in place of a formal test suite, and with plan.md's Technical
Context (no automated test suite introduced by this feature).

**Organization**: Tasks are grouped by user story (from spec.md, in priority order) so each story
is independently implementable, testable, and deliverable as an MVP increment.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US5, per spec.md)
- File paths below are exact and match `plan.md`'s Project Structure section

## Path Conventions

Single project, flat top-level packages (matches existing `Domain/`, `server.py` layout):
`egx_cli/`, `Domain/`, `.claude/skills/egx-cli/` at repository root — see plan.md.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project/package scaffolding so implementation work has somewhere to land

- [X] T001 Create the `egx_cli/` package skeleton: `egx_cli/__init__.py`, `egx_cli/commands/__init__.py` (empty modules, per plan.md Project Structure)
- [X] T002 Add `typer` to dependencies and a `[project.scripts] egx = "egx_cli.app:main"` entry in `pyproject.toml`, then run `uv sync` to install (research.md R2, R4)
- [X] T003 [P] Create `.claude/skills/egx-cli/SKILL.md` skeleton (research.md R7): frontmatter (name/description, matching this repo's existing `.claude/skills/speckit-*/SKILL.md` convention) plus an "Overview" section describing the CLI's purpose and the `--json`/`--verbose`/exit-code conventions from `contracts/cli-contract.md`; per-command sections are added in each user story's phase below (Constitution Principle VI)

**Checkpoint**: Package installs (`uv tool install .` or `uv run egx --help` resolves, even with zero subcommands registered yet).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared infrastructure every command depends on — no user story can start before this

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Implement shared output rendering in `egx_cli/output.py`: default-text and `--json` renderers for Price Quote, Price Series, Riser Result, Company/Ticker Entry, and Gold Price Quote, plus the Error Result shape and exit-code constants (0/1/2), all per `data-model.md` and `contracts/cli-contract.md`
- [X] T005 [P] Implement the per-command time-budget guard in `egx_cli/timing.py`: a `run_with_budget(fn, *args, budget_seconds, **kwargs)` helper using `ThreadPoolExecutor(max_workers=1).submit(...).result(timeout=budget_seconds)` that raises a clear timeout error for callers to render via `output.py` (research.md R3; 10s default, 30s override for riser commands)
- [X] T006 [P] Fix the `as_completed(futures, timeout=25)` loops in `Domain/download.py`'s `get_EGXdata` and `get_EGX_intraday_data` so a `concurrent.futures.TimeoutError` from the loop ends collection but keeps whatever results already landed in `close_prices_dic`, instead of discarding the whole batch (research.md R3 addendum — required for Constitution Principle III and spec SC-002 to actually hold for large ticker fan-outs)
- [X] T007 Create the Typer app skeleton in `egx_cli/app.py` (global `--json`/`--verbose` options, subcommand-group registration point, `main()` entry) and `egx_cli/__main__.py` (`python -m egx_cli` support), wired to import `output.py`/`timing.py` (depends on T004, T005)

**Checkpoint**: Foundation ready — `egx --help` runs cleanly; user story implementation can now begin.

---

## Phase 3: User Story 1 - Live price lookup for a known stock (Priority: P1) 🎯 MVP

**Goal**: An agent can reliably get a ticker's live price (falling back to last close) or last
daily close, within a 10s budget, with clear errors for invalid tickers.

**Independent Test**: `egx price live COMI` and `egx price last COMI` (and `--json` variants) per
`quickstart.md`; confirm output shape matches `contracts/cli-contract.md` and completes well
under 10s.

### Implementation for User Story 1

- [X] T008 [US1] Fix `EGXController.getLivePrice` in `Domain/egx_controller.py` to catch fetch failures (including the empty-DataFrame case when all underlying fetches fail) and fall back to `getLastDailyPrice`'s value, so FR-001's documented fallback behavior is actually true (currently the method raises `KeyError` on failure with no fallback — a pre-existing gap between the MCP docstring's claim and the implementation)
- [X] T009 [US1] Implement `egx price last <TICKER>` and `egx price live <TICKER>` in `egx_cli/commands/price.py`, calling `EGXController.getLastDailyPrice` / `getLivePrice` through `timing.run_with_budget` (10s), rendering via `output.py` as a Price Quote with `is_fallback` set correctly (depends on T008)
- [X] T010 [US1] Add ticker-argument validation in `egx_cli/commands/price.py` (empty/malformed ticker → exit code 1 with a one-line `Error: ...` on stderr, no network call attempted)
- [X] T011 [US1] Register the `price` command group in `egx_cli/app.py`
- [X] T012 [US1] Document `egx price last` / `egx price live` in `.claude/skills/egx-cli/SKILL.md`: when to use each, arguments, default vs. `--json` output shape, exit codes, and the fallback behavior

**Checkpoint**: User Story 1 fully functional and independently testable (MVP).

---

## Phase 4: User Story 2 - Resolve a company name to its ticker (Priority: P2)

**Goal**: An agent can list the full EGX company directory or resolve a company name to its
ticker(s), so it can feed a valid ticker into Story 1/3/4 commands.

**Independent Test**: `egx companies list` and `egx companies find "Commercial International"`
per `quickstart.md`; confirm the known-company case resolves to `COMI`.

### Implementation for User Story 2

- [X] T013 [US2] Add a `findTicker(query: str) -> dict[str, str]` case-insensitive substring-match helper to `EGXController` in `Domain/egx_controller.py` (research.md R1)
- [X] T014 [US2] Implement `egx companies list` and `egx companies find <QUERY>` in `egx_cli/commands/companies.py`, using `getEGXCompanies()` / `findTicker()`, rendering via `output.py` as Company/Ticker Entry array (empty match → exit 0, not an error, per spec Edge Cases)
- [X] T015 [US2] Register the `companies` command group in `egx_cli/app.py`
- [X] T016 [US2] Document `egx companies list` / `egx companies find` in `.claude/skills/egx-cli/SKILL.md`

**Checkpoint**: User Stories 1 and 2 both independently functional.

---

## Phase 5: User Story 3 - Periodic and intraday price history for a stock (Priority: P3)

**Goal**: An agent can get a ticker's historical daily-close series over a date range, or its
intraday series for one trading day, without pre-computing trading-day boundaries itself.

**Independent Test**: `egx history range COMI 2026-08-01 2026-09-01` and
`egx history intraday COMI 2026-09-04` per `quickstart.md`; confirm an empty-range request (e.g.
a weekend-only span) returns an empty result with exit 0, not an error.

### Implementation for User Story 3

- [X] T017 [US3] Implement `egx history range <TICKER> <START> <END>` and `egx history intraday <TICKER> <DATE>` in `egx_cli/commands/history.py`, calling `EGXController.getPriceChange` / `getIntraday` through `timing.run_with_budget` (10s), rendering via `output.py` as a Price Series; empty underlying series → empty `values` array with exit 0 (spec Edge Cases)
- [X] T018 [US3] Add ISO 8601 (`YYYY-MM-DD`) date-argument validation in `egx_cli/commands/history.py` (malformed date → exit code 1, no network call attempted, per spec Edge Cases)
- [X] T019 [US3] Register the `history` command group in `egx_cli/app.py`
- [X] T020 [US3] Document `egx history range` / `egx history intraday` in `.claude/skills/egx-cli/SKILL.md`

**Checkpoint**: User Stories 1–3 independently functional.

---

## Phase 6: User Story 4 - Top risers across the market within a bounded time (Priority: P4)

**Goal**: An agent can get the top-N risers over a period, or intraday today, across the full
~100-ticker universe, completing within a 30s budget every time — the capability directly
implicated in the known MCP timeout incident this feature fixes.

**Independent Test**: `egx risers period 2026-08-28 2026-09-04` and
`egx risers intraday --count 3` per `quickstart.md`; confirm default text output is capped to
rank/ticker/latest price/% change (not full series) and completes within 30s.

### Implementation for User Story 4

- [X] T021 [US4] Implement rank/`pct_change`/`latest_price` computation over `EGXController.getPeriodRisers` / `getIntradayRiser`'s `{ticker: [prices]}` output in `egx_cli/commands/risers.py`, producing the Riser Result shape from `data-model.md`
- [X] T022 [US4] Implement `egx risers period <START> <END> [--count N=5]` and `egx risers intraday [--count N=5]` in `egx_cli/commands/risers.py`, calling through `timing.run_with_budget` (30s); default text output limited to rank/ticker/latest_price/pct_change per ticker (FR-015 — full `values` series only under `--json`); no usable data → empty `results` array with exit 0 (spec Edge Cases)
- [X] T023 [US4] Register the `risers` command group in `egx_cli/app.py`
- [X] T024 [US4] Document `egx risers period` / `egx risers intraday` in `.claude/skills/egx-cli/SKILL.md`, noting the bounded-time guarantee for agents that may recall the old MCP tool's timeout behavior

**Checkpoint**: User Stories 1–4 independently functional.

---

## Phase 7: User Story 5 - Live gold prices (Priority: P5)

**Goal**: An agent can get current sell/buy gold prices across the standard karats.

**Independent Test**: `egx gold` per `quickstart.md`; confirm sell/buy values for each covered
karat.

### Implementation for User Story 5

- [X] T025 [US5] Implement `egx gold` in `egx_cli/commands/gold.py`, calling `GoldController.getCurrentGoldPrices()` through `timing.run_with_budget` (10s), rendering via `output.py` as a Gold Price Quote array
- [X] T026 [US5] Register the `gold` command in `egx_cli/app.py`
- [X] T027 [US5] Document `egx gold` in `.claude/skills/egx-cli/SKILL.md`

**Checkpoint**: All five user stories independently functional.

---

## Phase 8: Polish & Cross-Cutting Concerns (Linux)

**Purpose**: Documentation, SC-006 validation, and final Linux-side verification across all
stories. Linux (Ubuntu/Fedora) is this project's native development platform, so this phase is
where the feature is considered functionally complete and done *for Linux*; Windows parity is a
separate, dedicated gate (Phase 9) rather than bundled in here — see C3 in this feature's
`/speckit-analyze` report.

- [X] T028 [P] Add an install/usage section to `README.md` for the new `egx` CLI (`uv tool install .`, pointing at `quickstart.md` for examples); explicitly mark `server.py`/the MCP server as deprecated in favor of `egx` for Claude Cowork and Claude Code (Claude Desktop continues using the MCP server, per spec Assumptions), without removing it
- [X] T029 Document the confirmed invocation mechanism for both target hosts in `.claude/skills/egx-cli/SKILL.md`: Claude Code invokes `egx` via its Bash tool; Claude Cowork invokes it via a Skill capable of local code execution, reading this same file to learn which subcommand to run (research.md R6 — resolved, not an open question)
- [X] T030 [P] Measure SC-006 directly: using only `.claude/skills/egx-cli/SKILL.md` (no other context), have a fresh agent session attempt a representative set of stock/gold-price questions covering each command family (live price, company lookup, history, risers, gold) and record the fraction correctly routed to the right subcommand on the first attempt; confirm it meets or exceeds the 90% target, or note the gap if not
- [X] T031 Walk through every example in `quickstart.md` end-to-end on Linux (Ubuntu or Fedora); confirm each command's exit code, time budget, and default/`--json` output shape match `contracts/cli-contract.md` and `data-model.md`; specifically re-verify `egx risers ...` against SC-002 now that T006's partial-results fix is in place — this is the authoritative Linux confirmation for every command in the contract
- [X] T032 [P] Final pass over `.claude/skills/egx-cli/SKILL.md`: confirm every command in `contracts/cli-contract.md` is documented, with no stale or missing references (Constitution Principle VI)

**Checkpoint**: Feature is functionally complete and verified on Linux. Windows parity (Phase 9) is the remaining gate before the feature as a whole is "done" per Constitution Principle II.

---

## Phase 9: Windows Verification

**Purpose**: Confirm the parity Constitution Principle II requires, on the platform not used for
development. Runs after Phase 8 rather than interleaved with it, per explicit user decision during
`/speckit-analyze` remediation (finding C3): Linux is validated continuously through Phases 3–8;
Windows gets one dedicated, final pass using the already-Linux-verified commands and arguments as
its baseline.

- [ ] T033 Install `egx` on a Windows 10+ machine via `uv tool install .` (or `pipx install .`); confirm the generated console-script shim (`egx.exe`) resolves on `PATH` and `egx --help` runs without error
- [ ] T034 Re-run every command in `contracts/cli-contract.md` and every example in `quickstart.md` on that Windows machine, using the exact same arguments validated in T031's Linux walkthrough; confirm identical exit codes and output shape (Constitution Principle II, spec SC-005, FR-013)
- [ ] T035 Record and resolve any Windows-specific discrepancy surfaced by T034 (e.g. path separators, shell quoting of arguments with spaces, line-ending differences in output) before considering the feature done on Windows; re-run T034 after any fix

**Checkpoint**: Feature is verified equivalent on Linux and Windows — spec SC-005 and Constitution Principle II are both satisfied with evidence, not assumption.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories (every command needs `output.py`, `timing.py`, and `app.py`'s registration point; T006's `download.py` fix underpins US3/US4's reliability guarantees specifically)
- **User Stories (Phase 3–7)**: All depend on Foundational completion; independent of each other (US2–US5 do not require US1, etc.) and may proceed in any order or in parallel — priority order (P1→P5) is the recommended sequential path
- **Polish/Linux (Phase 8)**: Depends on all desired user stories being complete
- **Windows Verification (Phase 9)**: Depends on Phase 8 completion — it re-uses Phase 8's Linux-validated commands/arguments as its baseline, so it cannot start first

### User Story Dependencies

- **US1 (P1)**: No dependencies on other stories
- **US2 (P2)**: No dependencies on other stories (its `findTicker` addition is independent of US1's `getLivePrice` fix, even though both touch `egx_controller.py` — see Parallel Opportunities note below)
- **US3 (P3)**: No dependencies on other stories
- **US4 (P4)**: No dependencies on other stories
- **US5 (P5)**: No dependencies on other stories

### Within Each User Story

- Command implementation before `app.py` registration before `SKILL.md` documentation (documentation describes the finished command contract, not a moving target)
- Each story's `SKILL.md` task touches the same shared file as every other story's `SKILL.md` task — do not run two stories' documentation tasks in parallel; sequence them (any order) even though the stories' code tasks themselves are otherwise independent

### Parallel Opportunities

- T001 and T002 can run in parallel (different files); T003 can run alongside them
- T004, T005, and T006 can run in parallel (three different files: `output.py`, `timing.py`, `download.py`); all three must finish before T007
- Once Phase 2 completes, most user story *code* tasks can be built in parallel by different contributors, since each owns its own `egx_cli/commands/*.py` file — the one exception is that **US1's T008 and US2's T013 both edit `Domain/egx_controller.py`** (different methods, same file); sequence those two specifically rather than running them in parallel, even though the two stories are otherwise independent
- T028, T029, T030, and T032 in Phase 8 can all run in parallel with each other; T031 depends on all Phase 3–7 commands being implemented (it walks the finished CLI end-to-end) but not on T028/T029/T030/T032
- T033 (Phase 9) depends on Phase 8 being complete; T034 depends on T033; T035 depends on T034

---

## Parallel Example: Foundational Phase

```bash
# Launch in parallel (three different files, no interdependency):
Task: "Implement shared output rendering in egx_cli/output.py"
Task: "Implement per-command time-budget guard in egx_cli/timing.py"
Task: "Fix as_completed partial-results handling in Domain/download.py"
# Then, once all three land:
Task: "Create the Typer app skeleton in egx_cli/app.py and egx_cli/__main__.py"
```

## Parallel Example: Across User Stories (post-Foundational)

```bash
# Each of these touches a distinct command file and can proceed independently
# (NOTE: sequence T008 and T013 relative to each other — same Domain/egx_controller.py file):
Task: "T008 [US1] Fix getLivePrice fallback in Domain/egx_controller.py"
Task: "T017 [US3] Implement history commands in egx_cli/commands/history.py"
Task: "T021 [US4] Implement risers rank/pct_change computation in egx_cli/commands/risers.py"
Task: "T025 [US5] Implement gold command in egx_cli/commands/gold.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup) and Phase 2 (Foundational)
2. Complete Phase 3 (US1 — live/last price, including the `getLivePrice` fallback fix)
3. **STOP and VALIDATE**: run the US1 Independent Test above
4. This alone already fixes the primary stated pain point (reliable live/periodic price access) for the single-ticker case

### Incremental Delivery

1. Setup + Foundational → foundation ready (includes the `download.py` partial-results fix)
2. US1 (live/last price, with a real fallback) → validate → MVP usable by an agent
3. US2 (company lookup) → validate → agent no longer needs pre-known tickers
4. US3 (history/intraday series) → validate → "periodic prices" fully covered
5. US4 (bounded-time risers) → validate → the known timeout incident is directly addressed
6. US5 (gold) → validate → full parity with the prior MCP tool set reached
7. Polish (Phase 8) → documentation, SC-006 measurement, and full Linux validation → feature is functionally done for Claude Code and Claude Cowork on Linux
8. Windows Verification (Phase 9) → re-validate the same commands on Windows 10+ → feature is done, full-stop

### Suggested MVP Scope

User Story 1 (live/last price lookup) — it is the single most requested capability per spec.md
and delivers value with the smallest slice (2 commands, one small `Domain/` fix).

## Notes

- No dedicated test-writing tasks were generated (tests not explicitly requested in spec.md, and
  plan.md's Technical Context intentionally does not introduce a test suite); Phase 8's
  quickstart-validation task (T031) and Phase 9's Windows re-validation are the verification
  mechanism instead.
- Every `[Story]`-labeled task maps 1:1 to a functional requirement and/or command in
  `contracts/cli-contract.md` — cross-check there if a task's scope is unclear.
- Commit after each task or logical group; stop at any checkpoint to validate a story
  independently before moving to the next.
- Three targeted `Domain/` changes are in scope for this feature and no others: `findTicker`
  (T013), the `getLivePrice` fallback fix (T008), and the `as_completed` partial-results fix in
  `download.py` (T006). `Domain/download.py`'s retry/parallelism structure otherwise already
  exists on this branch and is not redesigned by any task above.
- FR-012 (bounded, fast-fail retry behavior) has no dedicated task in this file — it is already
  satisfied by existing code: `Domain/download.py` already applies `@retry(tries=3, delay=0.3)` to
  every fetch function on this branch. Noted here for traceability so it doesn't read as an
  oversight when cross-checking `contracts/cli-contract.md`/`spec.md` against this task list.
- Host scope (Claude Cowork, Claude Code) and the invocation mechanism for each are settled
  decisions as of 2026-09-05 (research.md R6) — T029 documents that decision, it does not
  investigate an open question. Claude Desktop is intentionally out of scope for this feature.
- **T030 result (SC-006)**: a fresh agent given only `.claude/skills/egx-cli/SKILL.md`'s content
  (no other context, no execution) correctly routed 7/7 representative questions across all five
  command families (live price, name→ticker lookup, history range/intraday, both risers commands,
  gold) to the right `egx` subcommand on the first attempt — 100%, exceeding the 90% target.
- **Post-implementation fix (user-reported)**: `--verbose` was declared as an option on every
  command (T009/T014/T017/T022/T025) but never actually wired to anything — `Domain/`'s and
  `tvDatafeed`'s log noise (WARNING/INFO lines) always reached stderr regardless of the flag,
  visible whenever stderr wasn't redirected away. Added `egx_cli/logging_setup.py`
  (`logging.disable()`, the one mechanism that overrides every logger's own level regardless of
  name) and call it as the first line of every command, gated on the actual `--verbose` value.
  This is what FR-009/FR-010 and Constitution Principle IV ("verbose/debug output is opt-in
  only") already required — the CLI just didn't do it yet.
- **Post-implementation fix #2 (user-reported)**: the above fix verified clean under `uv run` but
  the user still saw noise via the actual installed `uv tool install .` binary, for two separate
  reasons, both now fixed:
  1. `uv tool install .` is a no-op when the same package version is already installed (this
     project's version never changes on every edit), so the installed binary was silently still
     the pre-fix build. `uv tool install . --reinstall` forces a rebuild — documented in
     `README.md` and `quickstart.md` so this doesn't surprise the next person either.
  2. Once actually rebuilt, a *second*, unrelated noise source appeared on the first invocation
     only: `tvDatafeed`'s own `SyntaxWarning`s (invalid escape sequences in its source) fire from
     the *compiler* the first time that source is compiled in a given environment (i.e. once per
     fresh install, before bytecode is cached) — reproduced deterministically by clearing
     `tvDatafeed`'s `__pycache__`. The original `warnings.filterwarnings(..., module="tvDatafeed")`
     in `egx_cli/app.py` never actually matched this (confirmed empirically with a cleared cache);
     changed to an unscoped `category=SyntaxWarning` filter, verified clean on a cold cache too.
- **T031 surfaced a real, pre-existing bug**, now fixed as part of this pass:
  `Domain/egx_controller.py`'s `getPriceChange` called `logger.info(type(response), response)` —
  two positional args against a message with no `%` placeholders — which crashed Python's logging
  formatter and printed a spurious traceback to stderr on every `history range` call. Changed to
  `logger.debug(f"...")` (correct f-string, and debug- rather than info-level, since it's a full
  DataFrame dump). This was not caused by any task above; it predates this feature and would have
  affected the MCP server's equivalent tool identically.
- **T031 also surfaced a non-bug but noteworthy runtime behavior**: `egx gold` currently fails
  with exit 2 (`'NoneType' object has no attribute 'find'`) because `Domain/gold_controller.py`'s
  scraper can no longer parse the live gold-era.eg page (reproduces identically calling
  `GoldController` directly, unrelated to any change in this feature). The CLI's own error
  handling behaved exactly per contract (clean one-line stderr message, exit 2, no traceback) —
  this is a pre-existing external-site issue outside this feature's scope, not a CLI defect.
