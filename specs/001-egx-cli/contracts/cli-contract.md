# CLI Contract: `egx`

This is the external interface this feature exposes — to invoking agents (Claude Cowork, Claude
Code) and to the companion Skill document, which must describe exactly this surface. Any change to a command's name, arguments, or output shape is a contract change and
requires updating `.claude/skills/egx-cli/SKILL.md` in the same change (Constitution Principle VI).

## Global conventions

- Binary name: `egx`.
- Every data-returning command accepts `--json` (structured output, see data-model.md) and
  defaults to concise text (research.md R5) when omitted.
- Every command accepts `--verbose` to opt into diagnostic logging on stderr (Constitution
  Principle IV) — never on by default.
- Dates are ISO 8601 `YYYY-MM-DD`, passed as plain string arguments — no separate date-helper
  command exists (spec FR-017).
- Exit codes: `0` success (including "no data found" — that's a valid empty result, not a
  failure); `1` invalid input (bad ticker format, bad date, N out of range); `2` upstream/timeout
  failure (data source unreachable or command's time budget exceeded). Exact non-zero code values
  are part of this contract and must stay stable for agents that branch on exit status.
- stdout carries only the command's result (text or JSON); stderr carries errors, `--verbose`
  diagnostics, and nothing else.

## Commands

### `egx price last <TICKER>`

Last daily closing price. → **Price Quote** (`is_fallback` always `false`).
Time budget: 10s. Maps to FR-002 / User Story 1.

### `egx price live <TICKER>`

Current live price, falling back to last close. → **Price Quote**.
Time budget: 10s. Maps to FR-001 / User Story 1.

### `egx companies list`

Full company directory. → array<**Company/Ticker Entry**>.
Time budget: 10s (local data, no network). Maps to FR-003 / User Story 2.

### `egx companies find <QUERY>`

Case-insensitive substring match of `QUERY` against company names. → array<**Company/Ticker
Entry**> (possibly empty; empty is exit 0, not an error).
Time budget: 10s (local data, no network). Maps to FR-003 / User Story 2.

### `egx history range <TICKER> <START> <END>`

Historical daily closes between `START` and `END` inclusive. → **Price Series**.
Time budget: 10s. Maps to FR-004 / User Story 3.

### `egx history intraday <TICKER> <DATE>`

Intraday readings for one trading day. → **Price Series** (`start == end == DATE`).
Time budget: 10s. Maps to FR-005 / User Story 3.

### `egx risers period <START> <END> [-n/--count N=5]`

Top-N tickers by gain across the covered universe over `[START, END]`. → **Riser Result**.
Time budget: 30s. Maps to FR-006 / User Story 4.

### `egx risers intraday [-n/--count N=5]`

Top-N tickers by today's intraday gain across the covered universe. → **Riser Result**
(`start == end ==` today).
Time budget: 30s. Maps to FR-007 / User Story 4.

### `egx gold`

Current gold sell/buy prices per karat. → array<**Gold Price Quote**>.
Time budget: 10s. Maps to FR-008 / User Story 5.

## Out of scope for this contract

- No `egx date ...` / "current time" commands (spec FR-017 — dropped from the prior MCP tool set).
- No write/mutation commands — every command above is read-only.
