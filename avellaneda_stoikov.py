"""
Avellaneda-Stoikov market making (Avellaneda & Stoikov, 2008, "High-frequency
trading in a limit order book"). Reuses BaseMarketMaker's on_fills/on_tick/history
machinery (see market_maker.py) -- only the pricing model differs:

  reservation price   r(s, q, t) = s - q * gamma * sigma^2 * (T - t)
  optimal spread      delta(t)   = gamma * sigma^2 * (T - t) + (2 / gamma) * ln(1 + gamma / k)

  bid = r - delta / 2
  ask = r + delta / 2

where:
  s      = current mid-price -- the "true" fair value the model conditions on.
  q      = self.inventory (positive = long).
  gamma  = risk aversion. Larger gamma skews harder against inventory and
           quotes wider. Not order-1 -- see the scale note below.
  sigma  = volatility of the reference price, same time units as timestamp.
  T - t  = time remaining until the trading horizon. This is the FINITE-HORIZON
           variant: as t -> T, both the skew and the spread shrink toward
           (2/gamma)*ln(1+gamma/k), i.e. the model stops caring about inventory
           risk right as the session ends -- a known limitation, not a bug.
           Worth plotting inventory vs. time-of-day in a backtest to see it happen.
  k      = order-book liquidity / fill-intensity decay parameter (market order
           arrival rate falls off as exp(-k * distance_from_mid)). Treat as a
           constant for now -- calibrating it from data is a later step.

"""

import numpy as np

from market_maker import BaseMarketMaker


def reservation_price(mid_price, inventory, gamma, sigma, time_remaining):
    """
    r(s, q, t) = s - q * gamma * sigma^2 * (T - t)
    """
    return mid_price - inventory * gamma * sigma**2 * time_remaining


def optimal_spread(gamma, sigma, time_remaining, k):
    """
    delta(t) = gamma * sigma^2 * (T - t) + (2 / gamma) * ln(1 + gamma / k)

    """
    return gamma * sigma**2 * time_remaining + (2 / gamma) * np.log(1 + gamma / k)


class AvellanedaStoikovMarketMaker(BaseMarketMaker):
    def __init__(self, gamma, sigma, k, terminal_time, quote_size, max_inventory=None):
        super().__init__(quote_size)
        self.gamma = gamma
        self.sigma = sigma
        self.k = k
        self.terminal_time = terminal_time
        self.max_inventory = max_inventory

    def compute_quotes(self, order_book, timestamp):
        s = order_book.mid_price() if order_book.mid_price() is not None else self.reference_price
        time_remaining = max(0, self.terminal_time - timestamp)
        r = reservation_price(s, self.inventory, self.gamma, self.sigma, time_remaining)
        spread = optimal_spread(self.gamma, self.sigma, time_remaining, self.k)
        bid_price = r - spread / 2
        ask_price = r + spread / 2

        if self.max_inventory is not None:
            if self.inventory >= self.max_inventory:
                bid_price = None  # already at/over the long cap -- stop buying
            if self.inventory <= -self.max_inventory:
                ask_price = None  # already at/over the short cap -- stop selling

        return (bid_price, ask_price)
