# Phase 1 Data Model: EGX CLI Tool

All entities below are read-only, in-memory response shapes returned by CLI commands (via
`--json`); none are persisted by the CLI itself. Field names/shapes are the CLI's own contract —
they mirror but do not have to match `Domain/` internals exactly (the CLI is free to normalize
pandas output into plain JSON-serializable types).

## Company/Ticker Entry

Represents one EGX-listed company from the existing `egx_controller` directory.

| Field | Type | Notes |
|---|---|---|
| `name` | string | Full company name, as in `egx_controller.__egx30_companies_dict` |
| `ticker` | string | Ticker symbol (e.g. `COMI`) |

Source: `Domain/egx_controller.py` `__egx30_companies_dict` (existing), plus new `findTicker()`
helper (research.md R1) for the filtered/`find` case.

## Price Quote

A single price value for one ticker at a point in time.

| Field | Type | Notes |
|---|---|---|
| `ticker` | string | Ticker symbol |
| `price` | number | The price value |
| `is_fallback` | boolean | `true` if this is the last daily close returned because live data was unavailable (`price live` only; always `false` for `price last`) |

Source: `EGXController.getLivePrice` / `getLastDailyPrice` (existing, unchanged).

## Price Series

An ordered sequence of prices for one ticker across a date range (`history range`) or across one
trading day's intraday readings (`history intraday`).

| Field | Type | Notes |
|---|---|---|
| `ticker` | string | Ticker symbol |
| `start` | string (ISO date) | Requested start date (or trading date for intraday) |
| `end` | string (ISO date) | Requested end date (same as `start` for intraday) |
| `values` | array<number> | Ordered price points; empty array if no trading data exists for the range (spec Edge Cases) |

Source: `EGXController.getPriceChange` / `getIntraday` (existing, unchanged).

## Riser Result

A ranked set of up to N tickers by price gain for a period or for today's intraday session.

| Field | Type | Notes |
|---|---|---|
| `start` | string (ISO date) | Period start (or today's date for intraday) |
| `end` | string (ISO date) | Period end (same as `start` for intraday) |
| `requested_n` | integer | The N the caller asked for |
| `results` | array<RiserEntry> | Up to `requested_n` entries, ranked by `pct_change` descending; may be shorter than `requested_n` if fewer tickers had usable data (spec Edge Cases); empty array if none did |

**RiserEntry** (nested):

| Field | Type | Notes |
|---|---|---|
| `rank` | integer | 1-based rank within this result |
| `ticker` | string | Ticker symbol |
| `latest_price` | number | Most recent price in the underlying series |
| `pct_change` | number | Percent change from first to last price in the underlying series |
| `values` | array<number> | Full underlying price series — present in `--json` output only; omitted from default text output (spec FR-015) |

Source: `EGXController.getPeriodRisers` / `getIntradayRiser` (existing `__getRisers`, unchanged) —
the CLI computes `pct_change`/`rank`/`latest_price` from the existing `{ticker: [prices]}` return
shape rather than changing `Domain/`'s return contract.

## Gold Price Quote

| Field | Type | Notes |
|---|---|---|
| `karat` | string | Karat identifier (e.g. `21K`) |
| `sell` | number | Sell price |
| `buy` | number | Buy price |

Source: `GoldController.getCurrentGoldPrices` (existing, unchanged) — already matches the `GoldPrice`
Pydantic model used by `server.py`.

## Error Result (non-zero exit paths)

Not a "data" entity returned on stdout, but a consistent shape for stderr messages across all
commands so an agent can pattern-match failures without a JSON schema (default mode) or via
`--json` (structured mode):

| Field | Type | Notes |
|---|---|---|
| `error` | string | Short, human-readable message (e.g. `"unknown ticker: XYZ"`, `"request exceeded its time budget"`) |
| `command` | string | Which subcommand failed (e.g. `"price live"`) |

Default mode prints `error` as a single stderr line prefixed `Error: `; `--json` mode (when the
caller passed `--json` before the failure was known) prints `{"error": "...", "command": "..."}`
to stderr instead, keeping the stdout/stderr and JSON-shape contracts uniform even on failure.
