# EGX-MCP 📈

Egyptian Exchange (EGX) stock market data and live gold prices, for AI agents, via two
integration surfaces:

- **`egx` CLI** — for **Claude Cowork** and **Claude Code**, which invoke it directly as a
  subprocess. This is the primary, actively-developed surface going forward.
- **MCP server** (`server.py`) — for **Claude Desktop** (chat), which connects to it over MCP
  stdio. Kept in place and unmodified; considered **deprecated** for any client that can use the
  CLI instead.

---

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [The `egx` CLI (Claude Cowork / Claude Code)](#the-egx-cli-claude-cowork--claude-code)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Available Tools](#available-tools)
- [Available Resources](#available-resources)
- [Example Prompts](#example-prompts)
- [Tech Stack](#tech-stack)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- 🔴 **Live & closing stock prices** for EGX-listed companies
- 📊 **Intraday price readings** with 1-minute granularity
- 📅 **Historical price changes** over custom time periods
- 🏆 **Top rising stocks** — both intraday and over a date range
- 🥇 **Live gold prices** across 5 karats (buy & sell)
- 🗓️ **Date utilities** for easy time period calculations
- 🤖 **MCP-compatible** — plug directly into Claude Desktop or any MCP client

---

## Project Structure

```
egx-mcp/
│
├── server.py                   # MCP server entry point (Claude Desktop) — deprecated for Cowork/Code
│
├── egx_cli/                    # `egx` CLI entry point (Claude Cowork, Claude Code)
│   ├── app.py                  # Typer app; registers all subcommands
│   ├── commands/                # price, companies, history, risers, gold
│   ├── output.py                # shared text/--json rendering, exit codes
│   └── timing.py                # per-command time-budget enforcement
│
└── Domain/
    ├── egx_controller.py       # EGX stock data logic (prices, intraday, risers) — shared by both surfaces
    ├── gold_controller.py      # Gold price scraper — shared by both surfaces
    └── date_parser.py          # Date formatting utility
```

---

## The `egx` CLI (Claude Cowork / Claude Code)

Install it from this repo:

```bash
uv tool install .
```

This registers the `egx` command (`egx.exe` on Windows) via `uv`/`pipx`'s standard console-script
mechanism — no separate packaging step per platform.

> **If you already have `egx` installed and pulled newer code**, plain `uv tool install .` will
> silently do nothing — `uv` sees the same package version already installed and skips rebuilding
> from the changed source. Use `uv tool install . --reinstall` to force it to pick up local
> changes.

```bash
egx price live COMI                 # current price, falls back to last close
egx companies find "Commercial International"
egx history range COMI 2026-08-01 2026-09-01
egx risers period 2026-08-25 2026-09-01 --count 3
egx gold
```

Add `--json` to any command for structured output. Full command reference, arguments, and output
shapes: [`.claude/skills/egx-cli/SKILL.md`](.claude/skills/egx-cli/SKILL.md) — this is also what
Claude Code and Claude Cowork read to know how to invoke `egx`. See
[`specs/001-egx-cli/quickstart.md`](specs/001-egx-cli/quickstart.md) for more examples and
[`specs/001-egx-cli/contracts/cli-contract.md`](specs/001-egx-cli/contracts/cli-contract.md) for
the full interface contract (exit codes, time budgets, JSON schemas).

---

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) — fast Python package and project manager

## Install `uv` if you haven't already

## Installation

1. **Clone the repository**

```bash
git clone https://github.com/your-username/egx-mcp.git
cd egx-mcp
```

2. **Install dependencies**

```bash
uv sync
```

> This will automatically create a virtual environment and install all dependencies from `pyproject.toml`. Required packages include: `mcp[cli]`, `egxpy`, `requests`, `beautifulsoup4`

---

## Configuration

The sections below (Configuration through Available Resources) describe the **MCP server**, used
by **Claude Desktop** only. If you're setting this up for Claude Cowork or Claude Code, use the
[`egx` CLI](#the-egx-cli-claude-cowork--claude-code) above instead.

### Claude Desktop

Add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "egx-mcp": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/egx-mcp", "run", "server.py"]
    }
  }
}
```

---

## Usage

### Running the server directly

```bash
uv run server.py
```

### Using with the MCP CLI

```bash
uv run mcp dev server.py
```

Once connected to a compatible client (e.g., Claude Desktop), you can interact with the server through natural language.

---

## Available Tools

| Tool                     | Description                                                                     |
| ------------------------ | ------------------------------------------------------------------------------- |
| `get_current_time`       | Returns the current local date and time                                         |
| `get_timeperiod_date`    | Calculates a past date given today's date and a number of days                  |
| `get_last_price`         | Returns the last closing price for a given stock ticker                         |
| `get_live_price`         | Returns the live price for a stock (falls back to closing price if unavailable) |
| `get_price_change`       | Returns a list of daily prices between two dates for a given ticker             |
| `get_intraday_readings`  | Returns 1-minute intraday price readings for a stock on a given day             |
| `get_risers_overtime`    | Returns the top N stocks that gained the most over a given period               |
| `get_riser_intraday`     | Returns the top N stocks that gained the most today (intraday)                  |
| `get_current_gold_price` | Returns live buy and sell prices for 5 gold karats                              |

---

## Available Resources

| Resource      | URI               | Description                                                                        |
| ------------- | ----------------- | ---------------------------------------------------------------------------------- |
| EGX Companies | `egx://companies` | Returns the full dictionary of EGX-listed companies mapped to their ticker symbols |

---

## Example Prompts

Once connected to Claude Desktop, try asking:

> _"What is the current price of COMI?"_

> _"Which EGX stocks rose the most this week?"_

> _"Show me the intraday price readings for SWDY today."_

> _"What is today's gold price per karat in Egypt?"_

> _"How has FWRY performed over the last month?"_

> _"What are the top 3 rising stocks today?"_

---

## Tech Stack

| Package                                                                 | Purpose                                       |
| ----------------------------------------------------------------------- | --------------------------------------------- |
| [`uv`](https://docs.astral.sh/uv/)                                      | Fast Python package and project manager       |
| [`mcp`](https://github.com/modelcontextprotocol/python-sdk) / `FastMCP` | MCP server framework                          |
| [`egxpy`](https://pypi.org/project/egxpy/)                              | EGX market data (OHLCV, intraday, historical) |
| `requests`                                                              | HTTP requests for gold price scraping         |
| `beautifulsoup4`                                                        | HTML parsing for gold price data              |

---

## License

This project is licensed under the [MIT License](LICENSE).
