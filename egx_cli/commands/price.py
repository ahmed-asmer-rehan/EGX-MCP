"""`egx price ...` -- live and last-close stock prices (contracts/cli-contract.md)."""

import typer

from Domain.egx_controller import EGXController
from egx_cli import logging_setup, output, timing

app = typer.Typer(help="Live and last-close stock prices.")
_controller = EGXController()


def _validate_ticker(ticker: str, command: str, json_mode: bool) -> str:
    normalized = ticker.strip().upper()
    if not normalized or not normalized.isalnum():
        output.invalid_input(f"invalid ticker: {ticker!r}", command, json_mode=json_mode)
    return normalized


@app.command("last")
def last(
    ticker: str = typer.Argument(..., help="EGX ticker symbol, e.g. COMI"),
    json_: bool = typer.Option(False, "--json", help="Output structured JSON."),
    verbose: bool = typer.Option(False, "--verbose", help="Print diagnostics to stderr."),
) -> None:
    """Last daily closing price for TICKER."""
    logging_setup.configure(verbose)
    command = "price last"
    ticker = _validate_ticker(ticker, command, json_)
    try:
        price = timing.run_with_budget(
            _controller.getLastDailyPrice, ticker, budget_seconds=timing.DEFAULT_BUDGET_SECONDS
        )
    except timing.BudgetExceededError as exc:
        output.timeout_failure(str(exc), command, json_mode=json_)
    except Exception as exc:
        output.upstream_failure(str(exc), command, json_mode=json_)
        return
    output.price_quote(ticker, price, is_fallback=False, json_mode=json_)


@app.command("live")
def live(
    ticker: str = typer.Argument(..., help="EGX ticker symbol, e.g. COMI"),
    json_: bool = typer.Option(False, "--json", help="Output structured JSON."),
    verbose: bool = typer.Option(False, "--verbose", help="Print diagnostics to stderr."),
) -> None:
    """Current live price for TICKER, falling back to last close if live data is unavailable."""
    logging_setup.configure(verbose)
    command = "price live"
    ticker = _validate_ticker(ticker, command, json_)
    try:
        price, is_fallback = timing.run_with_budget(
            _controller.getLivePriceWithFallbackFlag, ticker, budget_seconds=timing.DEFAULT_BUDGET_SECONDS
        )
    except timing.BudgetExceededError as exc:
        output.timeout_failure(str(exc), command, json_mode=json_)
    except Exception as exc:
        output.upstream_failure(str(exc), command, json_mode=json_)
        return
    output.price_quote(ticker, price, is_fallback=is_fallback, json_mode=json_)
