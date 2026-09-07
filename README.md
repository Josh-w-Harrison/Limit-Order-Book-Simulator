# Limit Order Book Simulator

A limit order book matching engine, built from scratch in Python, along with
a simulator that can drive it with three different kinds of market data:
synthetic random order flow, synthetic order flow shaped around a real
historical price series, and a full order-by-order replay of real exchange
data. All three run through the exact same matching engine and the same
interactive visualization, so the project also doubles as a testbed for two
market-making strategies and a backtester built on top of realistic order
flow rather than just toy data.

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

On top of that sit two market-making strategies sharing a common base class
(`market_maker.py`, `avellaneda_stoikov.py`) and a backtester (`backtest.py`)
with a grid-search parameter optimizer, including a train/test split on the
LOBSTER data so parameters are never selected and evaluated on the same
period. See [Market-making strategies](#market-making-strategies) below.

## Market-making strategies

Two strategies run through the same order book and simulator, sharing all
non-pricing logic -- fill tracking, cancel-and-replace, the crossing clamp,
per-tick history -- via a `BaseMarketMaker` base class. Each subclass
implements only `compute_quotes()`, the one method that turns the current
state into a `(bid_price, ask_price)` pair.

**`MarketMaker`**: a simple inventory-skew quoter. Quotes sit at
`reference_price ± half_spread`, with the midpoint shifted against current
inventory (`skew_coefficient * inventory`) to encourage trading back to flat.

**`AvellanedaStoikovMarketMaker`**: finite-horizon Avellaneda-Stoikov
(Avellaneda & Stoikov, 2008). Reservation price and spread come from

```
r(s, q, t) = s - q * gamma * sigma^2 * (T - t)
delta(t)   = gamma * sigma^2 * (T - t) + (2/gamma) * ln(1 + gamma/k)
```

where `gamma` is risk aversion, `sigma` is reference-price volatility, `k` is
an order-book liquidity/fill-intensity parameter, and `(T - t)` is time
remaining until a trading horizon. As `t -> T`, both terms shrink toward the
liquidity floor `(2/gamma)*ln(1+gamma/k)` -- a known property of the
finite-horizon model: it stops pricing inventory risk right as the session
ends, rather than actively working to flatten into the close.

It also supports an optional `max_inventory` risk limit: once inventory
reaches the cap on either side, that side's quote is withheld for the tick
(`compute_quotes` returning `None` for a side is a contract
`BaseMarketMaker.on_tick` treats identically to a crossing quote), capping
directional exposure.

### Parameter tuning findings

Both strategies are tuned with the same grid-search/train-test-split
infrastructure in `backtest.py`, run against a real trading day of LOBSTER
order flow (AMZN, 2012-06-21). For Avellaneda-Stoikov:

- **`k` (liquidity/fill-intensity) has a sweet spot, not a monotonic best
  direction.** `k=20` (narrow spread) loses badly to adverse selection;
  `k=3` (very wide spread) also loses, just from being filled too rarely to
  earn anything. `k=5`-`k=10` was the peak among the values tried.
- **A tighter `max_inventory` cap consistently outperformed a looser one** --
  25 beat 50 beat 100 at every matching gamma/sigma/k -- staying closer to
  flat won on this data.
- **`gamma` turned out to be untestable with the current train/test split.**
  The split is chronological by row count, and `terminal_time` is pinned to
  the real session close, so the entire test window sits at a small
  `(T - t)`, where the finite-horizon model has already decayed the
  inventory-skew term to near zero regardless of `gamma`. Two runs with
  `gamma` differing by 100x produced identical trade counts and PnL within
  0.1% on the test set. That's not "gamma doesn't matter" -- it's a real gap
  in the current backtest design (see Future Additions).
- Best combination found: `gamma=1e-4, sigma=0.01, k=10, max_inventory=25`,
  giving a train PnL of +21.70 and a test PnL of +2.45 on this single
  stock-day.

## Future additions

- A genuine short-horizon predictive signal (order-flow imbalance,
  microprice, queue position) for either market maker to trade on. Grid
  search against real LOBSTER data reaches only modest, inconsistent PnL for
  both strategies (see Parameter tuning findings above) -- expected for
  strategies with no edge beyond reacting to their own inventory and the
  book's static liquidity profile.
- Calibrate `k` from real data instead of guessing it: fit LOBSTER's type-4
  (execution) rows' `|trade_price - mid_at_execution|` against arrival rate
  to estimate the exponential decay `k` in `lambda(delta) = A * exp(-k * delta)`.
- A train/test split that can actually exercise high-`(T - t)` behavior --
  e.g. across multiple session-days rather than chronologically within a
  single one -- so `gamma` can be genuinely validated instead of
  structurally starved of signal.
- Let Avellaneda-Stoikov actively cross to flatten when its own model calls
  for it, as an alternative (or complement) to the hard `max_inventory` cap.
- Integer minimum-increment tick prices instead of plain floats, to avoid
  floating-point representation-error bugs in price comparisons.
- Multi-asset support: `OrderBook` has no cross-asset state, so this would
  be a thin `dict[ticker -> OrderBook]` routing layer rather than a rewrite.
