"""`egx companies ...` -- EGX company directory and name lookup (contracts/cli-contract.md)."""

import typer

from Domain.egx_controller import EGXController
from egx_cli import logging_setup, output

app = typer.Typer(help="EGX company directory and ticker lookup.")
_controller = EGXController()


@app.command("list")
def list_all(
    json_: bool = typer.Option(False, "--json", help="Output structured JSON."),
    verbose: bool = typer.Option(False, "--verbose", help="Print diagnostics to stderr."),
) -> None:
    """Full EGX company-name-to-ticker directory."""
    logging_setup.configure(verbose)
    output.company_entries(_controller.getEGXCompanies(), json_mode=json_)


@app.command("find")
def find(
    query: str = typer.Argument(..., help="Company name or partial name to search for."),
    json_: bool = typer.Option(False, "--json", help="Output structured JSON."),
    verbose: bool = typer.Option(False, "--verbose", help="Print diagnostics to stderr."),
) -> None:
    """Case-insensitive substring search of company names; empty match is not an error."""
    logging_setup.configure(verbose)
    if not query.strip():
        output.invalid_input("query must not be empty", "companies find", json_mode=json_)
    output.company_entries(_controller.findTicker(query), json_mode=json_)
