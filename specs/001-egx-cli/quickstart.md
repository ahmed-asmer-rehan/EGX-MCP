# Quickstart: EGX CLI Tool

## Install (Linux or Windows)

```bash
uv tool install .
```

This installs the `egx` command (`egx.exe` on Windows) from this repo's `pyproject.toml`, reusing
the project's existing `uv`-based toolchain. `pipx install .` works identically as an alternative.

**Re-installing after a source change**: `uv tool install .` alone is a no-op if `egx` is already
installed at the same package version (the version in `pyproject.toml` doesn't change on every
commit) — it will keep running the old build. Use `uv tool install . --reinstall` to force it to
rebuild from the current source.

## Verify

```bash
egx --help
```

## Example invocations

```bash
# Live price for Commercial International Bank (falls back to last close if market is closed)
egx price live COMI

# Same, structured for a calling agent
egx price live COMI --json

# Resolve a company name to its ticker
egx companies find "Commercial International"

# Historical closes for a date range
egx history range COMI 2026-08-01 2026-09-01

# Today's intraday readings
egx history intraday COMI 2026-09-04

# Top 5 gainers this week
egx risers period 2026-08-28 2026-09-04

# Top 3 intraday gainers today
egx risers intraday --count 3

# Live gold prices
egx gold
```

## Expected behavior to sanity-check after implementation

- Every command above returns within its documented time budget (10s single-ticker /
  local-data commands, 30s for `risers ...`) even with no `--json` flag.
- `egx risers period ...` without `--json` prints one line per ticker (rank, ticker, latest
  price, % change) — not full price series.
- Every command works identically when run on a Windows 10+ shell and on Ubuntu/Fedora bash with
  the same arguments.
- An invalid ticker (e.g. `egx price live NOTATICKER`) exits non-zero with a one-line `Error: ...`
  message on stderr, no stack trace.
- The full agent-facing description of each command lives in `.claude/skills/egx-cli/SKILL.md`,
  not duplicated here.
