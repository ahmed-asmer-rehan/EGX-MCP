"""`egx gold` -- live gold prices across karats (contracts/cli-contract.md)."""

import typer

from Domain.gold_controller import GoldController
from egx_cli import logging_setup, output, timing

app = typer.Typer(help="Live gold sell/buy prices.")
_controller = GoldController()


@app.callback(invoke_without_command=True)
def gold(
    json_: bool = typer.Option(False, "--json", help="Output structured JSON."),
    verbose: bool = typer.Option(False, "--verbose", help="Print diagnostics to stderr."),
) -> None:
    """Current live gold sell/buy prices for each standard karat."""
    logging_setup.configure(verbose)
    command = "gold"
    try:
        quotes = timing.run_with_budget(
            _controller.getCurrentGoldPrices, budget_seconds=timing.DEFAULT_BUDGET_SECONDS
        )
    except timing.BudgetExceededError as exc:
        output.timeout_failure(str(exc), command, json_mode=json_)
        return
    except Exception as exc:
        output.upstream_failure(str(exc), command, json_mode=json_)
        return
    output.gold_prices(quotes, json_mode=json_)
