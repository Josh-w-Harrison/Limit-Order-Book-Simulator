# Limit Order Book Simulator

A limit order book matching engine, built from scratch in Python, along with
a simulator that can drive it with three different kinds of market data:
synthetic random order flow, synthetic order flow shaped around a real
historical price series, and a full order-by-order replay of real exchange
data. All three run through the exact same matching engine and the same
interactive visualization, so the project also doubles as a testbed for an
inventory-skew market-making strategy and a backtester built on top of
realistic order flow rather than just toy data.

The core idea: an order book is just bids and asks resting at price levels,
matched in price-then-time priority. Everything else in this project (the
tick-based simulator, the three market data sources, order expiry, the
visualization) exists to generate realistic *flow* into that book and let
you watch what happens to price, spread, and depth as a result.

## What it does

Given an order book and a source of order flow, the simulator steps through
events one at a time: submissions get matched against the resting book or
rest on it themselves, cancellations and partial reductions remove or shrink
resting orders, and every step is recorded (best bid/ask, mid price, spread,
depth, any trades) into a history you can replay afterwards.

Three interchangeable sources of that order flow:

- **Synthetic**: orders generated around a random-walk reference price,
  arriving at a Poisson-distributed rate per tick.
- **Historical**: the same synthetic order generation, but the reference
  price is driven by a real historical series (fetched from Yahoo Finance)
  instead of a random walk.
- **Real order flow**: a full replay of an actual trading day's order book
  activity, sourced from [LOBSTER](https://lobsterdata.com)'s reconstructed
  NASDAQ data: real submissions, cancellations, partial reductions, and
  executions, in the order they actually happened.

Running any of the three produces the same interactive visualization: a
price chart (reference price, mid price, best bid, best ask) with a time
slider, and a live order book depth chart underneath showing exactly what
was resting on each side at that point in the simulation.

On top of that sits an inventory-skew market maker (`market_maker.py`) and a
backtester (`backtest.py`) with a grid-search parameter optimizer, including
a train/test split on the LOBSTER data so parameters are never selected and
evaluated on the same period.

## Future additions

- A genuine short-horizon predictive signal (order-flow imbalance,
  microprice, queue position) for the market maker to trade on. Grid search
  against real LOBSTER data only ever reaches roughly breakeven, never real
  profit, which is expected for a strategy with no edge beyond reacting to
  its own inventory.
- Full Avellaneda-Stoikov market making (time-horizon decay, order-arrival
  intensity, risk-aversion-derived spread) as a deliberate step up from the
  current simple inventory-skew strategy.
- Integer minimum-increment tick prices instead of plain floats, to avoid
  floating-point representation-error bugs in price comparisons.
- Multi-asset support: `OrderBook` has no cross-asset state, so this would
  be a thin `dict[ticker -> OrderBook]` routing layer rather than a rewrite.
