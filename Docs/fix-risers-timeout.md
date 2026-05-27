# Fix: MCP Timeout in Risers Tools

## Problem

`get_risers_overtime` and `get_riser_intraday` consistently triggered MCP error `-32001: Request timed out`. The MCP client enforces a 30-second timeout, but these tools needed 150+ seconds because they fetched data for all 101 EGX tickers sequentially, each opening a new WebSocket connection to TradingView.

### Root Causes

1. **101 sequential WebSocket connections** -- each `get_hist()` call in `tvDatafeed` creates a fresh WebSocket. No connection reuse, no parallelism.
2. **20 retries per ticker with 0.5s delay** -- a single failing ticker burned 10 seconds of pure retry delay before giving up.
3. **5000 bars hardcoded for intraday** -- the API maximum, when only ~310 bars are needed for a single trading day (~270 min session at 1-min intervals). Most data was fetched and discarded.
4. **Synchronous execution on FastMCP's event loop** -- FastMCP calls sync tool functions directly (`fn(**args)`), blocking all other MCP protocol activity (heartbeats, other tool calls) until the function returns.
5. **`TvDatafeedLive` used unnecessarily** -- added a `threading.Lock` and live-feed machinery for what were one-shot historical data calls. The `timeout=-1` parameter meant infinite lock wait, though in practice each call created a fresh instance so the lock was uncontested.

### Impact

- Both risers tools were completely unusable from any MCP client (Claude Desktop, MCP Inspector).
- No partial failure handling -- one bad ticker crashed the entire tool via `ZeroDivisionError` or `KeyError`.

---

## Changes

### Files Modified

- `server.py`
- `Domain/download.py`
- `Domain/egx_controller.py`

---

### 1. Reduced retry parameters (`Domain/download.py`)

Changed all three `@retry` decorators from `tries=20, delay=0.5` to `tries=3, delay=0.3`.

TradingView connection failures are typically persistent (server down, invalid symbol), not transient. 20 retries rarely recovered a failing ticker but added up to 10 seconds of delay per failure. With 3 retries at 0.3s, a failing ticker costs ~1 second total.

Applies to: `get_OHLCV_data`, `_get_intraday_close_price_data`, `_get_close_price_data`.

### 2. Computed intraday bar count (`Domain/download.py`)

Replaced hardcoded `n=5000` in `get_EGX_intraday_data` with `_compute_intraday_bars()`, which calculates the number of bars needed based on the interval and date range.

For a single-day query at 1-minute intervals, this requests ~310 bars instead of 5000. The function uses the `holidays` package (already a dependency) to count working days and caps at 5000 (the API maximum).

### 3. Parallelized multi-ticker fetching (`Domain/download.py`)

Replaced sequential `for stock in stock_list` loops in both `get_EGXdata` and `get_EGX_intraday_data` with `concurrent.futures.ThreadPoolExecutor(max_workers=10)`.

Each thread creates its own `TvDatafeed` instance (no shared state), so 10 tickers fetch concurrently. 101 tickers complete in ~11 batches. `as_completed(timeout=25)` enforces a ceiling 5 seconds under the MCP client timeout.

An empty-dict guard before `pd.concat` prevents crashes when all tickers fail.

### 4. Defensive error handling in risers calculation (`Domain/egx_controller.py`)

Replaced the dict comprehension in `__getRisers` with a try/except loop that skips tickers with:
- Fewer than 2 price points
- Zero opening price (division by zero)
- Any other data error

Returns `{}` if all tickers fail, instead of crashing.

### 5. Async risers tools (`server.py`)

Converted `get_risers_overtime` and `get_riser_intraday` from sync to `async def`, wrapping the blocking domain call in `anyio.to_thread.run_sync(..., abandon_on_cancel=True)`.

This unblocks FastMCP's event loop so the MCP protocol can continue functioning (heartbeats, cancellation) while the heavy work runs in a separate thread. `abandon_on_cancel=True` means if the client cancels (timeout), the awaitable completes immediately rather than waiting for the thread.

Single-ticker tools (`get_last_price`, `get_live_price`, etc.) remain synchronous -- they complete in 1-3 seconds and don't need this treatment.

### 6. Swapped `TvDatafeedLive` to `TvDatafeed` (`Domain/download.py`)

`get_OHLCV_data` and `_get_intraday_close_price_data` were using `TvDatafeedLive` for one-shot historical calls. This created an unnecessary `threading.Lock` per call and exposed the `timeout=-1` (infinite lock wait) parameter. Switched to the base `TvDatafeed` class, which is what these functions actually need.

---

## Expected Performance

| Metric | Before | After |
|--------|--------|-------|
| Typical duration (101 tickers) | ~150s+ | ~16s |
| Worst case | Unbounded (infinite lock wait) | ~25s (ThreadPoolExecutor ceiling) |
| Retries per failing ticker | 20 x 0.5s = 10s | 3 x 0.3s = ~1s |
| Intraday bars requested (single day) | 5000 | ~310 |
| Event loop blocked | Yes (entire duration) | No (offloaded to thread) |

---

## Verification

1. `uv run mcp dev server.py` -- open MCP Inspector
2. Call `get_riser_intraday` with today's date, `n_companies=5` -- should return within 25s
3. Call `get_risers_overtime` with a 7-day range, `n_companies=5` -- should return within 25s
4. Call `get_live_price` with ticker `COMI` -- verify single-ticker tools still work
5. Check server logs for `"Failed Stocks"` entries to confirm partial failures are handled gracefully
