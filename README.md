# Limit Order Book Simulator

A limit order book matching engine and market simulator, built from scratch in
Python. It supports synthetic order flow, real historical prices, and full
order-by-order replay of real exchange data (via [LOBSTER](https://lobsterdata.com)),
all driving the same matching engine, with an interactive visualization of
price evolution and book depth over time.

## Features

- **Matching engine** (`order_book.py`, `price_level.py`): price-time priority
  matching with FIFO ordering within a price level, partial fills, multi-level
  sweeps, cancellation, and partial-quantity reduction.
- **Three interchangeable market data sources**, all satisfying the same
  generator interface so `Simulator` never needs to know which one it's
  driving:
  - `MarketDataGenerator` — synthetic order flow around a random-walk
    reference price.
  - `HistoricalMarketDataGenerator` — synthetic order flow driven by a real
    historical price series (via `fetch_historical_data.py` / Yahoo Finance).
  - `LOBSTERMarketDataGenerator` — full replay of real order-by-order flow
    (submissions, cancellations, partial reductions, and executions) from
    LOBSTER's reconstructed NASDAQ message data.
- **Tick-based simulation** (`simulator.py`) with Poisson-distributed order
  arrivals per tick, order expiry, and fully deterministic output given a
  seed.
- **Interactive visualization** (`main.py`): a time slider over reference
  price / mid price / best bid / best ask, with a live order book depth chart
  underneath.

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate  # .venv\Scripts\activate on Windows
pip install -r requirements.txt

# Run the test suite
for f in tests/test_*.py; do PYTHONPATH=. python "$f"; done

# Run the interactive demo (synthetic, historical, and real-data sims in turn)
PYTHONPATH=. python main.py
```

## Getting real market data

`data/` is gitignored — none of this is checked in, so you'll need to fetch
it yourself:

- **Historical prices** (drives `HistoricalMarketDataGenerator`):
  ```bash
  python fetch_historical_data.py --ticker AAPL --period 1y --interval 1d
  ```
  Saves a CSV to `data/`.

- **Real order flow** (drives `LOBSTERMarketDataGenerator`): download a free
  sample from [lobsterdata.com](https://lobsterdata.com/info/DataSamples.php)
  and point `main.py`'s `build_lobster_history()` at the `_message_` CSV it
  gives you. LOBSTER's message file only logs events within the requested
  price-level window, so a deeper level (e.g. 10) gives a more complete
  reconstruction — see the design notes below.

## Project structure

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
| `market_maker.py`, `backtest.py` | Not yet implemented — see Roadmap |

## Design notes

A few decisions worth knowing about if you're reading the code:

- **Duck-typed generator interface**: every market data source exposes
  `next_event()` / `advance_tick()` / `get_reference_price()`. `Simulator`
  never uses `isinstance` — any object with that shape is a drop-in
  replacement, which is how the same matching engine and visualization code
  serve synthetic, historical, and real-replay data unchanged.
- **Poisson-batched vs. real-event replay**: `Simulator.run(n_ticks)` samples
  a Poisson-distributed number of orders per tick for synthetic/historical
  data; `Simulator.run_replay()` processes exactly one real event per tick
  for LOBSTER data, since the file itself determines how many events exist.
- **LOBSTER replay caveats**: the message file only logs events for orders
  "in the requested price range," so a meaningful fraction of
  cancellation/execution rows reference orders that were never logged as
  submitted (measured at ~27% on a level-1 sample). These are skipped rather
  than treated as errors — the reconstructed book is necessarily a subset of
  the true depth, not a bug.
- **Determinism**: a single seed drives both the market data generator's
  randomness and the simulator's own Poisson sampling, so an entire run is
  reproducible end to end.
- **Performance**: `OrderBook.get_depth()` slices the underlying sorted
  structure by position instead of scanning it, and `LOBSTERMarketDataGenerator`
  reads its CSV into plain Python lists up front rather than paying pandas'
  per-cell access cost on every event — together these took a ~260k-event
  real replay from ~129s to ~3.6s.

## Roadmap

- `market_maker.py` — an inventory-skew quoting strategy that reacts after
  every trade (the event-driven design above exists specifically to support
  this).
- `backtest.py` — orchestrates the simulator + strategy and reports PnL/
  inventory over a run.
