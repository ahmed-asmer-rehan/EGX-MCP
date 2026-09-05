# Feature Specification: EGX CLI Tool

**Feature Branch**: `001-egx-cli`
**Created**: 2026-09-04
**Status**: Draft
**Input**: User description: "Build EGX-CLI: a cross-platform command-line tool that exposes the existing EGX stock market data and live gold price capabilities — currently only available through the EGX-MCP server — as CLI subcommands, so it can be invoked directly by Claude Desktop, Claude Cowork, and Claude Code instead of through MCP stdio, with a companion Claude Skill teaching agents how to use it. Primary focus: getting live and periodic stock prices reliably, fixing the known MCP timeout issue on the risers commands."

**Amendment (2026-09-05, during `/speckit-analyze` remediation)**: Claude Desktop (chat) is
dropped as a target host. Claude Cowork uses the companion skill to know how to invoke the CLI
(the same mechanism Claude Code uses via its Bash tool), so both remaining hosts have a confirmed
invocation path — this also resolves the constitution-alignment finding (C1) raised by that
analysis. The body below is updated to reflect this; the Input line above is left verbatim as the
original request for history.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Live price lookup for a known stock (Priority: P1)

An AI agent (running inside Claude Cowork or Claude Code) is asked by its user
"what's the current price of COMI?" or "what did stock X close at?". The agent invokes the CLI
with the ticker and gets back the live price (falling back to the last daily close if live data
is unavailable) in a form it can read directly into its answer.

**Why this priority**: This is the single most common request type and the core value the tool
must deliver reliably — it is explicitly the primary focus of this feature.

**Independent Test**: Run the live-price subcommand with a valid EGX ticker (e.g. `COMI`) and
confirm it returns a single numeric price value in under the documented time budget, with no
manual follow-up needed to interpret the result.

**Acceptance Scenarios**:

1. **Given** the market is open and live data is available, **When** the agent requests the live
   price for a valid ticker, **Then** the CLI returns that ticker's current live price.
2. **Given** the market is closed or live data is temporarily unavailable, **When** the agent
   requests the live price for a valid ticker, **Then** the CLI returns the last daily closing
   price instead of failing, and indicates the value is a fallback.
3. **Given** an invalid or unknown ticker, **When** the agent requests its live price, **Then**
   the CLI exits with a non-zero status and a clear, short error message on stderr — not a stack
   trace.

---

### User Story 2 - Resolve a company name to its ticker (Priority: P2)

A user refers to a company by name (in English), not its ticker symbol. The agent needs to look
up the correct EGX ticker before it can request a price, or needs the full company/ticker
directory to answer "what stocks are covered?".

**Why this priority**: Every ticker-based command (Stories 1, 3, 4) depends on the agent having a
valid ticker; without a reliable lookup, the agent must guess or hallucinate ticker symbols.

**Independent Test**: Run the company-directory subcommand and confirm it returns the full
company-name-to-ticker mapping in a form the agent can search; confirm a name-based lookup for a
known company (e.g. "Commercial International Bank-Egypt (CIB)") returns ticker `COMI`.

**Acceptance Scenarios**:

1. **Given** the agent needs the full set of covered companies, **When** it requests the company
   directory, **Then** the CLI returns the complete company-name-to-ticker mapping.
2. **Given** the agent has a company name (exact or partial match) but not its ticker, **When** it
   looks up that name, **Then** the CLI returns the matching ticker(s), or a clear "no match"
   result if none is found.

---

### User Story 3 - Periodic and intraday price history for a stock (Priority: P3)

An agent is asked "how has stock X performed over the last month?" or "show me today's price
movement for X". The agent requests a historical price series (date range) or an intraday series
(single trading day) for a ticker.

**Why this priority**: This is the "periodic stock prices" half of the primary focus, distinct
from the single-point live/last price of Story 1.

**Independent Test**: Run the historical price-range subcommand for a valid ticker and a
recent date range, and separately the intraday subcommand for the current trading day; confirm
both return an ordered list of prices without requiring the caller to pre-compute trading-day
boundaries.

**Acceptance Scenarios**:

1. **Given** a valid ticker and a start/end date, **When** the agent requests the historical price
   series, **Then** the CLI returns the ordered list of closing prices across that range.
2. **Given** a valid ticker and today's date, **When** the agent requests intraday readings,
   **Then** the CLI returns the ordered list of intraday prices for that trading day.
3. **Given** a date range with no trading days (e.g. spans only a weekend or an Egypt public
   holiday), **When** the agent requests the price series, **Then** the CLI returns an empty
   result with a clear indication that no trading data exists for that range, rather than an
   error or a hang.

---

### User Story 4 - Top risers across the market within a bounded time (Priority: P4)

An agent is asked "which EGX stocks gained the most this week?" or "what are today's top
gainers?". The agent requests the top-N risers over a date range, or the top-N intraday risers for
today, across the full covered ticker list (~100 tickers).

**Why this priority**: This is the capability directly implicated in the known production
incident (MCP timeout errors caused by unbounded sequential fetching across all tickers); it is
lower priority than Stories 1–3 because it is a market-wide aggregate rather than a
single-stock lookup, but fixing its reliability is an explicit goal of this feature.

**Independent Test**: Run the period-risers subcommand for a recent date range and confirm it
returns the top-N tickers by gain within the documented time budget, with no unbounded hang;
repeat for the intraday-risers subcommand for the current trading day.

**Acceptance Scenarios**:

1. **Given** a valid date range and a requested count N, **When** the agent requests the top
   risers over that period, **Then** the CLI returns at most N tickers ranked by price gain,
   within the documented time budget, every time — not only when the network happens to be fast.
2. **Given** today's date, **When** the agent requests the top intraday risers, **Then** the CLI
   returns at most N tickers ranked by today's intraday gain within the documented time budget.
3. **Given** no ticker in the covered list has usable price data for the requested range (e.g.
   full data-source outage), **When** the agent requests top risers, **Then** the CLI returns an
   empty result with a clear message rather than hanging or crashing.

---

### User Story 5 - Live gold prices (Priority: P5)

An agent is asked "what's the price of gold today?". The agent requests current gold prices
across the standard karats.

**Why this priority**: Carried over from the existing MCP tool set for feature parity; lower
priority than the stock-price stories because it is a single, independent, low-risk lookup (one
external source, no multi-ticker fan-out, no known timeout history).

**Independent Test**: Run the gold-price subcommand and confirm it returns sell/buy prices for
each of the standard karats.

**Acceptance Scenarios**:

1. **Given** the gold price source is reachable, **When** the agent requests current gold prices,
   **Then** the CLI returns sell and buy prices for each covered karat.
2. **Given** the gold price source is unreachable, **When** the agent requests current gold
   prices, **Then** the CLI exits with a non-zero status and a clear error message rather than
   hanging.

---

### Edge Cases

- What happens when a command is invoked with a syntactically invalid date (not ISO 8601 /
  malformed)? → Clear validation error on stderr, non-zero exit, no network call attempted.
- What happens when the requested ticker exists in the company directory but the underlying data
  source has no data for it (delisted, suspended, etc.)? → Clear "no data" result, not a crash.
- What happens when N (requested count of risers) exceeds the number of tickers with valid data
  for the period? → Return as many as are available (up to the available count), not an error.
- What happens when the tool is invoked with no network connectivity at all? → All commands fail
  fast within their time budget with a clear connectivity-related error, not a hang.
- What happens when `--json` output is requested for a command that has no data to return? →
  Valid JSON representing an empty result (e.g. `[]` or `{}`), never empty stdout or malformed JSON.
- What happens on Windows vs. Linux for identical input? → Identical output shape and content for
  the same command and arguments (Constitution Principle II).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The CLI MUST provide a subcommand that returns the current live price for a given
  EGX ticker, falling back to the last daily closing price when live data is unavailable, and
  indicating in the output when a fallback value was used.
- **FR-002**: The CLI MUST provide a subcommand that returns the last daily closing price for a
  given EGX ticker.
- **FR-003**: The CLI MUST provide a subcommand that returns the full EGX company-name-to-ticker
  directory, and support looking up a ticker by company name (exact or partial match).
- **FR-004**: The CLI MUST provide a subcommand that returns the historical price series for a
  given ticker between a start date and an end date.
- **FR-005**: The CLI MUST provide a subcommand that returns the intraday price series for a
  given ticker on a given trading day.
- **FR-006**: The CLI MUST provide a subcommand that returns the top-N tickers by price gain over
  a given date range, drawn from the full covered ticker list.
- **FR-007**: The CLI MUST provide a subcommand that returns the top-N tickers by intraday price
  gain for the current trading day, drawn from the full covered ticker list.
- **FR-008**: The CLI MUST provide a subcommand that returns current live gold prices (sell and
  buy) for each standard karat.
- **FR-009**: Every data-returning subcommand MUST support a `--json` flag producing valid,
  machine-parseable JSON; without the flag, output MUST default to concise, human/agent-readable
  text sized for LLM context economy.
- **FR-010**: Every subcommand MUST write results to stdout and errors/diagnostics to stderr, and
  MUST return a non-zero exit code on failure and zero on success.
- **FR-011**: The multi-ticker aggregate subcommands (top risers over a period, top intraday
  risers) MUST complete or fail within a documented, bounded time budget regardless of how many
  of the ~100 covered tickers must be queried — they MUST NOT fetch tickers strictly sequentially
  with unbounded retries, which is the root cause of the known MCP timeout incident this feature
  replaces.
- **FR-012**: All data-fetching subcommands MUST use bounded, fast-fail retry behavior (per
  Constitution Principle III) rather than the prior long-retry behavior, so a single unreachable
  ticker cannot stall an entire request.
- **FR-013**: The CLI MUST run with identical command syntax, arguments, and output shape on
  Linux (Ubuntu, Fedora) and Windows 10+.
- **FR-014**: The CLI MUST ship with a companion Claude Skill document that tells an invoking
  agent, for each subcommand: when to use it, its required/optional arguments, and how to
  interpret its default and `--json` output.
- **FR-015**: Default (non-JSON) output for the top-risers subcommands MUST be summarized/capped
  rather than dumping full price series for every returned ticker, so response size stays bounded
  even when N is large.
- **FR-016**: When a subcommand's underlying data source returns no usable data for a valid
  request (e.g. no trading days in range, no gainers found), the CLI MUST return a clear empty
  result (not an error, not a hang) with exit code zero.
- **FR-017**: The CLI MUST accept dates as plain ISO 8601 (`YYYY-MM-DD`) arguments; it MUST NOT
  require the caller to invoke a separate "get current date" or "date math" command to construct
  a request (the date-helper conveniences that existed only for the prior MCP tool set are not
  carried over).

### Key Entities

- **Company/Ticker Entry**: A single EGX-listed company, identified by its full name and its
  ticker symbol; the unit returned by the company-directory lookup.
- **Price Quote**: A single price value for a ticker at a point in time, with an indicator of
  whether it is a live value or a last-close fallback.
- **Price Series**: An ordered sequence of price values for one ticker across a date range or
  across a single trading day's intraday readings.
- **Riser Result**: A ranked set of up to N tickers for a given period (date range or intraday),
  each with its associated price movement/series.
- **Gold Price Quote**: A karat identifier paired with a sell price and a buy price.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An agent can obtain a live or last-close price for a single valid ticker in under
  10 seconds, without a timeout, in at least 99% of requests.
- **SC-002**: An agent can obtain the top-N risers (period or intraday) across the full ~100-ticker
  universe in under 30 seconds, without a timeout, in at least 95% of requests — replacing the
  prior behavior where these requests routinely failed with a timeout error.
- **SC-003**: 100% of default-mode command outputs are single-purpose and require no
  post-processing by the calling agent beyond reading the value(s) directly into its answer.
- **SC-004**: 100% of `--json` command outputs are valid, parseable JSON matching the documented
  shape for that command, including for empty results.
- **SC-005**: The same command and arguments produce equivalent output on both a Linux (Ubuntu or
  Fedora) machine and a Windows 10+ machine, verified by spot-check for every shipped subcommand.
- **SC-006**: An agent with no prior exposure to this tool can determine the correct subcommand
  for a live-price, historical-price, riser, or gold-price question using only the shipped skill
  document, without any failed/misrouted invocation, in at least 90% of trial requests.

## Assumptions

- The CLI is a new adapter over the existing `Domain/` layer (`egx_controller`, `download`,
  `gold_controller`, `date_parser`); no new data source is introduced and no change to the
  underlying market-data provider is in scope.
- The covered ticker universe remains the existing EGX company list already maintained in
  `Domain/egx_controller.py`; expanding or maintaining that list is out of scope for this feature.
- No authentication/authorization is required — this is read-only, publicly available market and
  gold-price data, matching the current MCP server's access model.
- The date-helper conveniences present only for LLM scaffolding in the prior MCP tool set
  (`get_current_time`, `get_timeperiod_date`) are dropped; a CLI-invoking agent is assumed capable
  of producing an ISO 8601 date itself.
- "Bounded time budget" values in Success Criteria (10s single-ticker, 30s market-wide) are
  reasonable starting targets consistent with the constitution's fast-fail retry principle; exact
  numeric budgets may be refined during planning based on real data-source latency.
- The CLI is the primary, intended integration surface going forward — this reflects the explicit
  project direction to move off the MCP server, not an open question. `server.py`/the MCP server
  is NOT deleted by this feature (deleting a working integration surface in the same change that
  introduces its replacement is an unnecessary, avoidable risk); it is left in place, unmodified,
  and marked deprecated in project documentation, with its removal scoped as separate future
  cleanup once the CLI has reached parity and been validated by real usage.
- The two target hosts are Claude Cowork and Claude Code. Both have a confirmed mechanism to
  invoke a local CLI process: Claude Code via its Bash tool (directly demonstrable — this very
  planning work runs via that mechanism), and Claude Cowork via a Skill capable of local code
  execution, per explicit user confirmation during `/speckit-analyze` remediation. Claude Desktop
  (chat) is out of scope for this CLI and continues to use the existing MCP server. See
  plan.md/research.md R6 for the resolved decision record.
