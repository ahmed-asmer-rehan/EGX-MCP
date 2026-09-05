"""Typer app entry point for the egx CLI (contracts/cli-contract.md)."""

import os
import sys
import warnings

import typer

# tvDatafeed (a Domain/ dependency) has invalid escape sequences in its own source, which
# the compiler warns about the first time that source is compiled in a given environment
# (i.e. once per fresh install, before bytecode is cached -- reproduces by clearing
# tvDatafeed's __pycache__). SyntaxWarnings fire from the *compiler*, not from code running
# inside tvDatafeed's own namespace, so a module="tvDatafeed" filter never actually matches
# it (confirmed empirically) -- only an unscoped category filter reliably catches it.
warnings.filterwarnings("ignore", category=SyntaxWarning)

from egx_cli.commands import companies, gold, history, price, risers

app = typer.Typer(
    name="egx",
    help="Egyptian Exchange (EGX) stock and gold price data, for agent consumption.",
    add_completion=False,
    pretty_exceptions_enable=False,
    no_args_is_help=True,
)
app.add_typer(price.app, name="price")
app.add_typer(companies.app, name="companies")
app.add_typer(history.app, name="history")
app.add_typer(risers.app, name="risers")
app.add_typer(gold.app, name="gold")


def main() -> None:
    """
    Run the app, then hard-exit instead of letting the interpreter shut down normally.

    Any command that fetches data goes through Domain/download.py's ThreadPoolExecutor,
    whose worker threads are not daemonic. concurrent.futures registers an atexit hook
    that joins *every* such thread ever created before the interpreter is allowed to
    exit -- so if tvDatafeed is still retrying a rate-limited request in the background
    (observed in practice against the live API), a normal exit hangs on it even though
    this command already printed its result and finished successfully. That directly
    violates Constitution Principle III ("must not hang"), so every exit from here goes
    through os._exit(), which skips atexit entirely.
    """
    try:
        app()
    except SystemExit as exc:
        code = exc.code
        if not isinstance(code, int):
            code = 0 if code is None else 1
    else:
        code = 0
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)


if __name__ == "__main__":
    main()
