"""`egx history ...` -- historical and intraday price series (contracts/cli-contract.md)."""

from datetime import datetime

import typer

from Domain.egx_controller import EGXController
from egx_cli import logging_setup, output, timing

app = typer.Typer(help="Historical and intraday price series for a ticker.")
_controller = EGXController()

_DATE_FORMAT = "%Y-%m-%d"


def _parse_date(value: str, command: str, json_mode: bool) -> datetime:
    try:
        return datetime.strptime(value, _DATE_FORMAT)
    except ValueError:
        output.invalid_input(
            f"invalid date {value!r}, expected YYYY-MM-DD", command, json_mode=json_mode
        )


def _validate_ticker(ticker: str, command: str, json_mode: bool) -> str:
    normalized = ticker.strip().upper()
    if not normalized or not normalized.isalnum():
        output.invalid_input(f"invalid ticker: {ticker!r}", command, json_mode=json_mode)
    return normalized


@app.command("range")
def price_range(
    ticker: str = typer.Argument(..., help="EGX ticker symbol, e.g. COMI"),
    start: str = typer.Argument(..., help="Start date, YYYY-MM-DD"),
    end: str = typer.Argument(..., help="End date, YYYY-MM-DD"),
    json_: bool = typer.Option(False, "--json", help="Output structured JSON."),
    verbose: bool = typer.Option(False, "--verbose", help="Print diagnostics to stderr."),
) -> None:
    """Historical daily-close series for TICKER between START and END (inclusive)."""
    logging_setup.configure(verbose)
    command = "history range"
    ticker = _validate_ticker(ticker, command, json_)
    start_date = _parse_date(start, command, json_)
    end_date = _parse_date(end, command, json_)
    try:
        values = timing.run_with_budget(
            _controller.getPriceChange, end_date, start_date, ticker,
            budget_seconds=timing.DEFAULT_BUDGET_SECONDS,
        )
    except timing.BudgetExceededError as exc:
        output.timeout_failure(str(exc), command, json_mode=json_)
        return
    output.price_series(ticker, start, end, values, json_mode=json_)


@app.command("intraday")
def intraday(
    ticker: str = typer.Argument(..., help="EGX ticker symbol, e.g. COMI"),
    date: str = typer.Argument(..., help="Trading date, YYYY-MM-DD"),
    json_: bool = typer.Option(False, "--json", help="Output structured JSON."),
    verbose: bool = typer.Option(False, "--verbose", help="Print diagnostics to stderr."),
) -> None:
    """Intraday price series for TICKER on DATE."""
    logging_setup.configure(verbose)
    command = "history intraday"
    ticker = _validate_ticker(ticker, command, json_)
    trading_date = _parse_date(date, command, json_)
    try:
        values = timing.run_with_budget(
            _controller.getIntraday, ticker, trading_date,
            budget_seconds=timing.DEFAULT_BUDGET_SECONDS,
        )
    except timing.BudgetExceededError as exc:
        output.timeout_failure(str(exc), command, json_mode=json_)
        return
    except Exception:
        # No data for this ticker/date (non-trading day, delisted, etc.) is a valid
        # empty result, not a failure -- matches getPriceChange's own behavior and
        # spec Edge Cases ("no data" -> clear empty result, not a crash).
        values = []
    output.price_series(ticker, date, date, values, json_mode=json_)
