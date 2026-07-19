# Limit Order Book Simulator

A limit order book matching engine, built from scratch in Python, along with
a simulator that can drive it with three different kinds of market data:
synthetic random order flow, synthetic order flow shaped around a real
historical price series, and a full order-by-order replay of real exchange
data. All three run through the exact same matching engine and the same
interactive visualization, so the project doubles as a small testbed for
later strategy work (a market maker, backtesting) on top of realistic order
flow rather than just toy data.

The core idea: an order book is just bids and asks resting at price levels,
matched in price-then-time priority. Everything else in this project —
the tick-based simulator, the three market data sources, order expiry, the
visualization — exists to generate realistic *flow* into that book and let
you watch what happens to price, spread, and depth as a result.

## What it does

Given an order book and a source of order flow, the simulator steps through
events one at a time: submissions get matched against the resting book or
rest on it themselves, cancellations and partial reductions remove or shrink
resting orders, and every step is recorded (best bid/ask, mid price, spread,
depth, any trades) into a history you can replay afterwards.

Three interchangeable sources of that order flow:

- **Synthetic** — orders generated around a random-walk reference price,
  arriving at a Poisson-distributed rate per tick.
- **Historical** — the same synthetic order generation, but the reference
  price is driven by a real historical series (fetched from Yahoo Finance)
  instead of a random walk.
- **Real order flow** — a full replay of an actual trading day's order book
  activity, sourced from [LOBSTER](https://lobsterdata.com)'s reconstructed
  NASDAQ data: real submissions, cancellations, partial reductions, and
  executions, in the order they actually happened.

Running any of the three produces the same interactive visualization: a
price chart (reference price, mid price, best bid, best ask) with a time
slider, and a live order book depth chart underneath showing exactly what
was resting on each side at that point in the simulation.

## Design

The matching engine (`order_book.py`, `price_level.py`) does price-time
priority matching: FIFO ordering within a price level, partial fills, sweeps
across multiple price levels for a single incoming order, cancellation, and
partial-quantity reduction. `simulator.py` drives it tick by tick, handles
order expiry (resting orders get cancelled once they're older than a
configurable age), and guarantees fully deterministic output given a single
seed.

A few decisions worth knowing about if you're reading the code:

- **Duck-typed generator interface.** Every market data source — synthetic,
  historical, or LOBSTER — exposes the same three methods: `next_event()`,
  `advance_tick()`, `get_reference_price()`. `Simulator` never checks which
  kind it has; anything with that shape is a drop-in replacement. That's
  what lets the same matching engine and visualization serve all three data
  sources unmodified.
- **Two simulation modes.** `Simulator.run(n_ticks)` samples a
  Poisson-distributed number of orders per tick, for synthetic/historical
  data where "how many orders happen per tick" is something you're
  simulating. `Simulator.run_replay()` processes exactly one real event per
  tick instead, for LOBSTER data, since the file itself already determines
  how many events exist and when.
- **LOBSTER replay is necessarily incomplete, by design.** LOBSTER's message
  file only logs events for orders "in the requested price range" — an
  order resting outside the tracked window gets no submission record, but
  can still generate a cancellation or execution record later once it
  becomes top-of-book. Measured at ~27% of cancel/execution rows on a
  level-1 sample. These get skipped rather than treated as errors: the
  reconstructed book is always a subset of the true depth, which is a known
  limitation rather than a bug.
- **Determinism.** A single seed drives both the market data generator's
  own randomness and the simulator's Poisson sampling, so an entire run —
  every order, every trade, every tick boundary — is reproducible end to
  end.
- **Performance.** The first pass at LOBSTER replay took ~129 seconds for a
  ~260k-event trading day; profiling showed the cost wasn't the matching
  engine but `OrderBook.get_depth()` scanning the entire book on every tick
  just to return the top few levels, and pandas' per-cell access overhead
  in the CSV parser. Fixing both (positional slicing on the sorted book,
  and reading the CSV into plain Python lists once up front) brought that
  down to ~3.6 seconds.

### Project structure

| File | Purpose |
|---|---|
| `order.py` | `Order`, `order_side`/`order_type`/`market_event_type` enums |
| `price_level.py` | FIFO queue of resting orders at a single price |
| `order_book.py` | Bid/ask book, matching logic, cancel/reduce |
| `trade.py` | Executed trade record |
| `market_data.py` | The three market data generators + shared `MarketEvent` |
| `simulator.py` | Tick-driven simulation loop, order expiry, real-event replay |
| `fetch_historical_data.py` | Pulls historical OHLCV data via yfinance |
| `main.py` | Interactive matplotlib visualization |
| `tests/` | Unit tests for every module above |
| `market_maker.py`, `backtest.py` | Not yet implemented — see Future Additions |

## Using it

```bash
python -m venv .venv
source .venv/bin/activate  # .venv\Scripts\activate on Windows
pip install -r requirements.txt

# Run the test suite
for f in tests/test_*.py; do PYTHONPATH=. python "$f"; done

# Run the interactive demo (synthetic, historical, and real-data sims in turn)
PYTHONPATH=. python main.py
```

`data/` is gitignored, so you'll need to fetch your own market data:

- **Historical prices** (drives `HistoricalMarketDataGenerator`):
  ```bash
  python fetch_historical_data.py --ticker AAPL --period 1y --interval 1d
  ```
  Saves a CSV to `data/`.

- **Real order flow** (drives `LOBSTERMarketDataGenerator`): download a free
  sample from [lobsterdata.com](https://lobsterdata.com/info/DataSamples.php)
  and point `main.py`'s `build_lobster_history()` at the `_message_` CSV it
  gives you. A deeper level (e.g. 10 rather than 1) gives a more complete
  reconstruction, per the LOBSTER replay caveat above.

## Future additions

- **`market_maker.py`** — an inventory-skew quoting strategy that reacts
  after every trade. The event-driven design of the simulator (processing
  one event at a time rather than only in batches) exists specifically to
  support this.
- **`backtest.py`** — orchestrates the simulator and a strategy together
  and reports PnL/inventory over a run.
