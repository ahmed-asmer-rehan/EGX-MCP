---
name: "egx-cli"
description: "Look up Egyptian Exchange (EGX) stock prices, historical/intraday price series, top gainers, and live gold prices via the `egx` CLI. Use whenever asked about an EGX-listed company's price, EGX top gainers, or gold prices."
metadata:
  author: "egx-mcp"
user-invocable: false
disable-model-invocation: false
---

## Overview

`egx` is a command-line tool exposing Egyptian Exchange (EGX) stock market data and live gold
prices. Invoke it as a subprocess (Bash tool) — do not try to import it as a Python library.

It replaces the project's MCP server (`server.py`) as the integration surface for this kind of
question when you are running as Claude Code or Claude Cowork. If you are Claude Desktop (chat),
this CLI is not available to you — use the MCP server's tools instead.

### Installation (run once per environment, if `egx` isn't already on PATH)

```bash
uv tool install .
```

Run from the repo root (this project). This registers the `egx` console script via `uv`'s
standard mechanism — the same one used on both Linux and Windows, no separate per-OS step.

- **Claude Code**: run the above and subsequent `egx ...` commands via your Bash tool, same as
  any other shell command in this repo.
- **Claude Cowork**: run it via your code-execution capability the same way — this file is what
  you read to know which subcommand answers a given question; there is no other setup step.

### Conventions

- Binary name: `egx`. Every subcommand below is `egx <group> <action> [args...]`.
- Add `--json` to any data-returning command for structured, machine-parseable output. Omit it
  for concise text meant to be read directly into your answer — prefer this by default; reach for
  `--json` only when you need to compute over the result yourself (e.g. sorting, further
  filtering).
- Add `--verbose` to see diagnostic logging on stderr; never needed for normal use.
- Dates are plain `YYYY-MM-DD` strings. There is no separate "get current date" command — compute
  the date yourself before calling `egx`.
- **Exit codes**: `0` = success (an empty result, e.g. "no trading days in range," is still
  success — check the output, not just the exit code, to tell empty from missing). `1` = invalid
  input (bad ticker, bad date, bad count) — fix the arguments and retry. `2` = upstream/timeout
  failure (data source unreachable or the command's time budget was exceeded) — this is not your
  input's fault; you can retry once, but don't loop on it.
- stdout carries only the result. stderr carries errors and `--verbose` diagnostics.
- Every command completes within a documented time budget (10s for single-ticker/local-data
  commands, 30s for the two market-wide `risers` commands) — it will not hang.

## `egx price last <TICKER>`

Last daily closing price. Use for "what did X close at" / "yesterday's price of X" questions.

```
$ egx price last COMI
COMI 141.0
```

`--json`: `{"ticker": "COMI", "price": 141.0, "is_fallback": false}`

## `egx price live <TICKER>`

Current live price, falling back to the last close if live data is unavailable (e.g. market
closed). Use for "what's the current/live price of X" questions — this is the default choice for
a bare "price of X" question when the user doesn't specify "closing" or a date.

```
$ egx price live COMI
COMI 141.0 (fallback: last close)
```

`--json`: `{"ticker": "COMI", "price": 141.0, "is_fallback": true}` — check `is_fallback` before
telling the user this is a *live* price; when `true`, say it's the last close instead.

Both commands: exit 1 on a malformed ticker argument, exit 2 if the underlying data source
couldn't be reached at all (rare — `price live` already falls back before failing this way).

## `egx companies list`

Full company-name-to-ticker directory. Use when you need to browse all covered companies, or as a
last resort when `companies find` returns no match and you want to scan names yourself.

```
$ egx companies list
COMI    Commercial International Bank-Egypt (CIB)
SWDY    ELSWEDY ELECTRIC
...
```

## `egx companies find <QUERY>`

Case-insensitive substring search of company names. **Use this whenever the user names a company
in words rather than giving you a ticker directly** — resolve the ticker here first, then pass it
to `price`/`history`. An empty match is not an error (exit 0, prints `no match`) — try a shorter
or different substring of the name rather than giving up.

```
$ egx companies find "Commercial International"
COMI    Commercial International Bank-Egypt (CIB)
```

## `egx history range <TICKER> <START> <END>`

Historical daily-close series between START and END (inclusive, both `YYYY-MM-DD`). Use for "how
has X performed over [period]" questions. An empty `values` array (exit 0) means no trading data
exists for that range (e.g. it fell entirely on weekends/Egypt holidays) — not an error.

```
$ egx history range COMI 2026-08-25 2026-09-01
COMI: 138.1, 136.3, 139.0
```

## `egx history intraday <TICKER> <DATE>`

Intraday price series for one trading day (`YYYY-MM-DD`). Use for "today's price movement" /
"how did X move today" questions. Same empty-result convention as `history range`.

```
$ egx history intraday COMI 2026-09-04 --json
{"ticker": "COMI", "start": "2026-09-04", "end": "2026-09-04", "values": []}
```

Both commands: exit 1 on a malformed ticker or a date not in `YYYY-MM-DD` form; values are always
listed oldest-first.

## `egx risers period <START> <END> [--count N]`

Top-N gainers (default N=5) across the full covered EGX universe (~100 tickers) over a date
range. Use for "which stocks gained the most this [period]" questions. This command scans every
covered ticker, so it can legitimately take up to ~30 seconds — that is expected, not a hang; do
not retry it reflexively if it takes a while, only if it actually errors or you hit the timeout
message.

```
$ egx risers period 2026-08-25 2026-09-01 --count 3
1. ATLC 6.8 (+24.77%)
2. HDBK 115.8 (+17.16%)
3. AMOC 13.25 (+15.82%)
```

Default text output is capped to rank/ticker/latest price/percent change — it does **not** include
each ticker's full price series. Add `--json` if you need the full series (`values`) per ticker.

## `egx risers intraday [--count N]`

Same as `risers period`, but for today's intraday gain instead of a date range. No date arguments
— it always covers today.

```
$ egx risers intraday --count 2 --json
{"start": "2026-09-05", "end": "2026-09-05", "requested_n": 2, "results": []}
```

An empty `results` array (exit 0) means no ticker in the universe had usable data for the
period/day — not an error. This replaces the prior MCP tool set's `get_risers_overtime` /
`get_riser_intraday`, which routinely hit MCP timeout errors on this same request shape; these
commands are bounded and will not hang.

## `egx gold`

Current gold sell/buy prices for each standard karat. Use for "what's the price of gold today"
questions. No arguments.

```
$ egx gold
21K: sell=6250 buy=6200
...
```

Exit 2 if the gold price source is unreachable or its page structure has changed — this is an
upstream data-source issue, not something you can fix by retrying with different arguments.
