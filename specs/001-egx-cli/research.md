# Phase 0 Research: EGX CLI Tool

## R1: Company name → ticker lookup (FR-003)

**Decision**: Add a small `EGXController.findTicker(query: str) -> dict[str, str]` method that
does a case-insensitive substring match of `query` against the existing
`__egx30_companies_dict` keys (company names) and returns the matching `{name: ticker}` subset.
Reuse the existing dict; no new data source.

**Rationale**: `getEGXCompanies()` already returns the full dict for the "list all" case
(User Story 2, scenario 1); the CLI only needs a small, dependency-free search on top of data
that already lives in `egx_controller.py`. Doing this in `Domain/` (not in the CLI command
handler) keeps it reusable and consistent with Constitution Principle V (Reuse Over Rewrite) —
it's business logic (which companies match a name), not a CLI formatting concern.

**Alternatives considered**:
- *Fuzzy matching (e.g. `rapidfuzz`)* — rejected for v1: adds a dependency for a ~100-entry
  dict where the current MCP prompts already worked with a static resource dump; substring match
  is sufficient and the agent can retry with a different query on a miss. Revisit only if empty
  no-match results prove common in practice.
- *Push the lookup into the CLI layer instead of `Domain/`* — rejected: violates Principle V and
  would need duplicating if the logic is ever needed by another caller (e.g. a future MCP tool).

## R2: CLI framework

**Decision**: `Typer` (Click-based), with its default `rich`-formatted help/errors left OFF for
command *output* (only used for `--help` ergonomics) — command results always go through a
dedicated plain-text/JSON renderer in `egx_cli/output.py`, never Typer's default `print`/echo
styling.

**Rationale**: Typer gives type-hint-driven subcommands, automatic `--help`, and consistent
argument parsing with minimal boilerplate across ~8 commands and a shared `--json`/`--verbose`
global option set — meeting Principle I with the least code. It is pure Python, installs and runs
identically on Linux and Windows (Principle II), and is already a common, well-maintained
dependency (built on Click) so it doesn't introduce packaging risk.

**Alternatives considered**:
- *Stdlib `argparse`* — zero new dependency, but ~8 subcommands with shared global flags and
  per-command help text means materially more boilerplate for the same result; rejected as a
  false economy given Typer's dependency footprint is small and well-established.
- *Click directly (no Typer)* — viable, slightly more verbose per-command decorators than Typer's
  type-hint style; Typer preferred for readability, no functional difference for this scope.

## R3: Per-command time budget enforcement

**Decision**: Each CLI command wraps its call into `Domain/` in a
`concurrent.futures.ThreadPoolExecutor(max_workers=1).submit(...)` / `.result(timeout=BUDGET)`
guard in `egx_cli/timing.py`, where `BUDGET` is 10s for single-ticker commands (live/last price,
single-ticker history/intraday) and 30s for the two market-wide riser commands, per spec SC-001
and SC-002. On timeout, the command prints a concise "request exceeded its time budget" error to
stderr and exits non-zero — it does not wait indefinitely for a stuck network call.

**Rationale**: `Domain/download.py` already bounds its *internal* fan-out with a 25s
`as_completed(..., timeout=25)` on this branch, but that only bounds the parallel-fetch stage —
a single-ticker call path (`getLastDailyPrice`, `getLivePrice`) goes through `@retry(tries=3,
delay=0.3)` with no outer ceiling if the underlying `tv.get_hist` call itself blocks longer than
expected. An outer, CLI-level budget guard is the simplest way to make the "fails within a
documented time budget, never hangs" guarantee (spec Edge Cases, SC-001/SC-002) hold for *every*
command uniformly, without touching `Domain/` fetch internals (Principle V).

**Alternatives considered**:
- *Rely solely on `Domain/`'s existing timeouts* — rejected: covers the multi-ticker fan-out case
  but leaves single-ticker calls (`get_OHLCV_data`, `_get_intraday_close_price_data` called
  directly, not through the executor) with no outer bound.
  *Note: implementation tasks should re-check whether the observed floor for `tries=3, delay=0.3`
  network round-trips leaves enough headroom under a 10s budget; if not, either the CLI budget or
  the underlying retry policy needs adjusting — capture as a task, not decided here.*

**Addendum — a real gap found in `Domain/download.py`'s existing timeout, not just a missing
outer bound**: `get_EGXdata`/`get_EGX_intraday_data`'s `for future in as_completed(futures,
timeout=25)` loop raises `concurrent.futures.TimeoutError` from the loop itself if *any* future is
still pending at 25s — this discards whatever the other (possibly 90+) already-completed tickers
returned, rather than returning a partial riser/history result. For a ~100-ticker fan-out at
`max_workers=10`, one slow ticker can fail the entire batch. This directly undermines spec SC-002
("95% of requests succeed within 30s") and Constitution Principle III's "bounded, resilient"
guarantee, so fixing it is in scope for this feature (Foundational phase task) even though it
lives in `Domain/download.py` — it's a correctness fix to existing bounded-fetch behavior, not new
business logic, and leaving it broken means the CLI's outer 30s budget would still surface hard
failures instead of the graceful degraded/partial results the spec expects. Fix: wrap the loop
body so a `TimeoutError` from `as_completed` ends the loop but keeps whatever results were already
collected in `close_prices_dic`, instead of propagating and losing them.
- *`asyncio.wait_for` with an async rewrite of `Domain/`* — rejected: would mean rewriting the
  synchronous `Domain/` layer, violating Principle V for no benefit at this scale (~100 tickers,
  single CLI invocation per process).

## R4: Packaging / installation for Linux + Windows parity

**Decision**: Add `typer` to `pyproject.toml` dependencies and a `[project.scripts]` entry
(`egx = "egx_cli.app:main"`). Users/agents install via `uv tool install .` (or `pipx install .`)
from the repo, which is already the project's established toolchain (README already documents
`uv`). Both tools generate the correct platform-native shim (`egx` on Linux, `egx.exe` on
Windows) from the same `pyproject.toml` — no separate Windows-specific packaging step needed.

**Rationale**: The project already standardizes on `uv`; reusing it for the CLI avoids
introducing a second packaging toolchain. `uv tool install`/`pipx install` are both explicitly
designed for cross-platform console-script distribution, satisfying Principle II without bespoke
platform branches.

**Alternatives considered**:
- *PyInstaller-built standalone binaries per OS* — rejected as unnecessary complexity for v1: the
  target users already run `uv`-based Python tooling (Claude Code and Claude Cowork both operate
  alongside this repo); a compiled-binary distribution can be revisited later if agents need to
  invoke the CLI without a Python environment present at all.
- *Separate install scripts per OS* — rejected: directly contradicts Constitution Principle II's
  "no shell-specific assumptions ... as the sole path".

## R5: Default text output shape vs. `--json`

**Decision**: Default (non-JSON) output per command:
- `price last` / `price live`: a single line, `<ticker> <price>` (plus a `(fallback: last close)`
  suffix when live data fell back to last close).
- `companies list`: a compact `<ticker>\t<name>` table, one per line.
- `companies find <query>`: same shape, filtered to matches; `no match` line (exit 0) if none.
- `history range` / `history intraday`: `<ticker>: <p1>, <p2>, ..., <pN>` on one line (values
  comma-separated) rather than one line per price point, to stay information-dense.
- `risers period` / `risers intraday`: one line per returned ticker,
  `<rank>. <ticker> <latest_price> (<pct_change>%)` — NOT the full price series (that's
  `--json`-only), directly implementing spec FR-015.
- `gold`: one line per karat, `<karat>: sell=<sell> buy=<buy>`.

`--json` output for every command returns the full underlying data (full series for
history/risers, full mapping for companies) as a single JSON document on stdout, matching the
entities in data-model.md.

**Rationale**: Directly operationalizes Constitution Principle IV and spec FR-009/FR-015 with a
concrete, consistent shape agents can learn once from the skill doc and rely on everywhere.

**Alternatives considered**: Always emitting full series in default text — rejected, explicitly
called out in spec FR-015 as something that must NOT happen for the riser commands (risk of large,
context-expensive output for large N).

## R6: Host invocation mechanism (Claude Cowork / Claude Code) — RESOLVED

**Decision**: The target hosts for this CLI are Claude Cowork and Claude Code only. Claude Desktop
(chat) is out of scope — it continues to reach EGX data exclusively through the existing MCP
server. This was an open, explicitly-flagged assumption during initial planning (see history
below); it was resolved by explicit user decision during the `/speckit-analyze` remediation pass
on 2026-09-05, which also confirmed the mechanism for the remaining two hosts: Claude Code invokes
`egx` via its Bash tool (already in use throughout this repo — directly demonstrable, not
assumed); Claude Cowork invokes it via a Skill capable of local code execution, using
`.claude/skills/egx-cli/SKILL.md` (R7) to learn which subcommand to run. No fallback/checkpoint
task is needed for a third, unconfirmed host — there isn't one.

**Rationale**: Narrowing scope to the two hosts with a confirmed invocation path removes the
single largest source of risk this plan carried (whether the whole premise — a local CLI as an
MCP alternative — was even reachable for Desktop). Claude Desktop keeps working exactly as today,
unaffected, via the unmodified MCP server.

**History (superseded)**: The original plan (`/speckit-plan` on 2026-09-04) included Claude
Desktop as a third target host with its invocation mechanism assumed, not confirmed, and carried a
dedicated Polish-phase validation task to close that gap. `/speckit-analyze` flagged this as
finding C1 (HIGH — the constitution asserted subprocess invocation as settled fact for all three
hosts while the plan admitted it was unverified for two of them). The user resolved it directly by
dropping Desktop rather than continuing to carry the open question; the constitution was amended
to 1.1.0 to match (see `.specify/memory/constitution.md` Sync Impact Report).

## R7: Skill document discovery path

**Decision**: Place the companion skill at `.claude/skills/egx-cli/SKILL.md` (not a top-level
`skills/` directory) so it matches the convention this repository already uses for Claude Code
skill discovery (see `.claude/skills/speckit-*/` installed by spec-kit itself). This is also the
skill Claude Cowork reads to learn CLI invocation (R6) — its install/discovery step for Cowork is
documented directly in `SKILL.md` itself as part of implementation (tasks.md T029).

**Rationale**: For Claude Code, this is the only path that is actually auto-discovered — a
`skills/` directory at the repo root would simply never be picked up. Since both remaining target
hosts (R6) consume the same skill file, one correct, discoverable location serves both.

**Alternatives considered**: `skills/egx-cli/SKILL.md` at repo root (this plan's earlier draft) —
superseded by this decision once the discovery-path mismatch was identified.

## Outstanding NEEDS CLARIFICATION

None in the Technical Context sense — Technical Context in plan.md has no unresolved
`NEEDS CLARIFICATION` markers. R6 remains an explicitly-flagged open assumption (not a blocking
clarification) to be closed out by tasks.md's Polish-phase validation task.
