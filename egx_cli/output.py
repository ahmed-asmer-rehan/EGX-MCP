"""Shared output rendering and exit-code conventions for the egx CLI (contracts/cli-contract.md)."""

import json
import sys
from typing import Any, NoReturn

EXIT_OK = 0
EXIT_INVALID_INPUT = 1
EXIT_UPSTREAM_FAILURE = 2


def _emit_error(message: str, command: str, json_mode: bool) -> None:
    if json_mode:
        print(json.dumps({"error": message, "command": command}), file=sys.stderr)
    else:
        print(f"Error: {message}", file=sys.stderr)


def invalid_input(message: str, command: str, *, json_mode: bool) -> NoReturn:
    """Validation failed before any fetch started; a normal exit is safe here."""
    _emit_error(message, command, json_mode)
    raise SystemExit(EXIT_INVALID_INPUT)


def upstream_failure(message: str, command: str, *, json_mode: bool) -> NoReturn:
    """The fetch ran to completion (in-budget) and failed; a normal exit is safe here."""
    _emit_error(message, command, json_mode)
    raise SystemExit(EXIT_UPSTREAM_FAILURE)


def timeout_failure(message: str, command: str, *, json_mode: bool) -> NoReturn:
    """Budget was exceeded. See app.main() for why this doesn't need its own hard exit."""
    _emit_error(message, command, json_mode)
    raise SystemExit(EXIT_UPSTREAM_FAILURE)


def price_quote(ticker: str, price: float, is_fallback: bool, *, json_mode: bool) -> None:
    if json_mode:
        print(json.dumps({"ticker": ticker, "price": price, "is_fallback": is_fallback}))
        return
    suffix = " (fallback: last close)" if is_fallback else ""
    print(f"{ticker} {price}{suffix}")


def company_entries(entries: dict[str, str], *, json_mode: bool) -> None:
    """entries: {company_name: ticker}"""
    if json_mode:
        print(json.dumps([{"name": name, "ticker": ticker} for name, ticker in entries.items()]))
        return
    if not entries:
        print("no match")
        return
    for name, ticker in entries.items():
        print(f"{ticker}\t{name}")


def price_series(ticker: str, start: str, end: str, values: list[float], *, json_mode: bool) -> None:
    if json_mode:
        print(json.dumps({"ticker": ticker, "start": start, "end": end, "values": values}))
        return
    if not values:
        print(f"{ticker}: no trading data for {start}..{end}")
        return
    print(f"{ticker}: " + ", ".join(str(v) for v in values))


def riser_result(start: str, end: str, requested_n: int, results: list[dict[str, Any]], *, json_mode: bool) -> None:
    """results: [{rank, ticker, latest_price, pct_change, values}]"""
    if json_mode:
        print(json.dumps({"start": start, "end": end, "requested_n": requested_n, "results": results}))
        return
    if not results:
        print("no risers found")
        return
    for r in results:
        print(f"{r['rank']}. {r['ticker']} {r['latest_price']} ({r['pct_change']:+.2f}%)")


def gold_prices(quotes: list[dict[str, Any]], *, json_mode: bool) -> None:
    """quotes: [{karat, sell, buy}]"""
    if json_mode:
        print(json.dumps(quotes))
        return
    for q in quotes:
        print(f"{q['karat']}: sell={q['sell']} buy={q['buy']}")
