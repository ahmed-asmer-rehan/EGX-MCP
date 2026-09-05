"""`egx risers ...` -- top-N gainers across the covered ticker universe (contracts/cli-contract.md)."""

from datetime import datetime
from typing import Any

import typer

from Domain.egx_controller import EGXController
from egx_cli import logging_setup, output, timing

app = typer.Typer(help="Top-N EGX gainers over a period or intraday.")
_controller = EGXController()

_DATE_FORMAT = "%Y-%m-%d"


def _parse_date(value: str, command: str, json_mode: bool) -> datetime:
    try:
        return datetime.strptime(value, _DATE_FORMAT)
    except ValueError:
        output.invalid_input(
            f"invalid date {value!r}, expected YYYY-MM-DD", command, json_mode=json_mode
        )


def _validate_count(count: int, command: str, json_mode: bool) -> int:
    if count < 1:
        output.invalid_input(f"count must be >= 1, got {count}", command, json_mode=json_mode)
    return count


def _rank(raw: dict[str, list[float]]) -> list[dict[str, Any]]:
    """Turn {ticker: [prices]} (already top-N and gain-ranked by Domain/) into Riser Result entries."""
    entries = []
    for ticker, values in raw.items():
        values = [float(v) for v in values]
        first, last = values[0], values[-1]
        pct_change = ((last - first) / first) * 100 if first else 0.0
        entries.append({"ticker": ticker, "latest_price": last, "pct_change": pct_change, "values": values})
    entries.sort(key=lambda e: e["pct_change"], reverse=True)
    for i, entry in enumerate(entries, start=1):
        entry["rank"] = i
    return entries


def _strip_series_for_text(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{k: v for k, v in e.items() if k != "values"} for e in entries]


@app.command("period")
def period(
    start: str = typer.Argument(..., help="Period start date, YYYY-MM-DD"),
    end: str = typer.Argument(..., help="Period end date, YYYY-MM-DD"),
    count: int = typer.Option(5, "--count", "-n", help="Number of top risers to return."),
    json_: bool = typer.Option(False, "--json", help="Output structured JSON (includes full price series)."),
    verbose: bool = typer.Option(False, "--verbose", help="Print diagnostics to stderr."),
) -> None:
    """Top-N tickers by price gain across the covered universe over [START, END]."""
    logging_setup.configure(verbose)
    command = "risers period"
    start_date = _parse_date(start, command, json_)
    end_date = _parse_date(end, command, json_)
    count = _validate_count(count, command, json_)
    try:
        raw = timing.run_with_budget(
            _controller.getPeriodRisers, end_date, start_date, count,
            budget_seconds=timing.RISERS_BUDGET_SECONDS,
        )
    except timing.BudgetExceededError as exc:
        output.timeout_failure(str(exc), command, json_mode=json_)
        return
    entries = _rank(raw)
    results = entries if json_ else _strip_series_for_text(entries)
    output.riser_result(start, end, count, results, json_mode=json_)


@app.command("intraday")
def intraday(
    count: int = typer.Option(5, "--count", "-n", help="Number of top risers to return."),
    json_: bool = typer.Option(False, "--json", help="Output structured JSON (includes full price series)."),
    verbose: bool = typer.Option(False, "--verbose", help="Print diagnostics to stderr."),
) -> None:
    """Top-N tickers by today's intraday price gain across the covered universe."""
    logging_setup.configure(verbose)
    command = "risers intraday"
    count = _validate_count(count, command, json_)
    today = datetime.today()
    try:
        raw = timing.run_with_budget(
            _controller.getIntradayRiser, today, count,
            budget_seconds=timing.RISERS_BUDGET_SECONDS,
        )
    except timing.BudgetExceededError as exc:
        output.timeout_failure(str(exc), command, json_mode=json_)
        return
    entries = _rank(raw)
    results = entries if json_ else _strip_series_for_text(entries)
    today_str = today.strftime(_DATE_FORMAT)
    output.riser_result(today_str, today_str, count, results, json_mode=json_)
