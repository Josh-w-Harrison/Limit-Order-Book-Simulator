from sortedcontainers import SortedDict

from order import order_side
from price_level import PriceLevel
from trade import Trade

class OrderBook:
    """
    Single-asset limit order book / matching engine.

    Structure:
      - self.bids, self.asks: SortedDict mapping price -> PriceLevel.
        SortedDict keeps keys in ascending order, so:
          best bid (highest price) = self.bids.peekitem(-1)
          best ask (lowest price)  = self.asks.peekitem(0)
      - self.order_locations: dict[order_id -> (side, price)], for O(1)
        cancel lookup instead of scanning every price level.

    Design questions to think through before/while implementing:
      - When a new LIMIT order arrives, how do you decide whether it
        crosses the book at all before you even start matching? (A BUY at
        price P only matches if P >= best_ask; a SELL at price P only
        matches if P <= best_bid. If the book is empty on the opposite
        side, it can't cross.)
      - Once you know it crosses, how do you sweep -- one order at a time,
        one price level at a time -- until either the incoming order is
        fully filled or the book stops crossing? What does PriceLevel
        already give you to do this? (peek_front, fill_front, is_empty --
        see price_level.py)
      - After a price level is fully drained by matching, it must be
        removed from the SortedDict entirely -- an empty PriceLevel left
        sitting in self.bids/self.asks would make best_bid/best_ask wrong.
        Where exactly does that cleanup need to happen?
      - If the incoming order isn't fully filled by matching (or doesn't
        cross at all), the remainder needs to rest on the book. Which
        side? What if there's no PriceLevel at that price yet?
      - order_locations needs to be kept in sync at every step: created
        when an order starts resting, removed when an order is fully
        filled or cancelled. Where do partial fills fit in -- does the
        order's location entry change at all when it's partially filled
        but still resting at the same price?
      - trade.py doesn't exist yet. What should the matching loop return
        in the meantime -- e.g. a list of (resting_order_id, incoming_
        order_id, price, quantity) tuples -- so it can be wrapped into
        real Trade objects later without reworking the matching logic
        itself?
      - cancel_order: what should happen if the order_id doesn't exist?
        (Compare to the choice you already made in PriceLevel.remove_order.)
    """

    def __init__(self):
        self.bids = SortedDict()
        self.asks = SortedDict()
        self.order_locations = {}

    def add_order(self, order):
        """
        Entry point for a new incoming order. Should:
          1. Attempt to match the order against the opposite side of the
             book (sweeping multiple orders/levels as needed).
          2. If any quantity remains unfilled, rest it on the book on its
             own side, creating a new PriceLevel if needed.
          3. Keep order_locations in sync throughout.
          4. Return whatever record of what happened (fills, remaining
             resting order) that callers -- and eventually the strategy
             layer -- will need.
        """
        # Try to fill order against the opposite side of the book, one resting order at a time,
        # until either the incoming order is fully filled or the book stops crossing.
        trade_records = []
        while order.quantity > 0:
            if order.side == order_side.BUY:
                if not self.asks:
                    break  # no asks to match against
                best_ask_price, best_ask_level = self.asks.peekitem(0)
                if order.price < best_ask_price:
                    break  # incoming buy doesn't cross the book
                # Match against the best ask level
                trade_qty = min(order.quantity, best_ask_level.peek_front().quantity)
                resting_order = best_ask_level.peek_front()
                best_ask_level.fill_front(trade_qty)
                if resting_order.quantity == 0:
                    del self.order_locations[resting_order.order_id]
                order.quantity -= trade_qty
                if best_ask_level.is_empty():
                    del self.asks[best_ask_price]
                trade_records.append(Trade(
                    price=best_ask_price,
                    quantity=trade_qty,
                    buy_order_id=order.order_id,
                    sell_order_id=resting_order.order_id
                ))
            else:  # SELL
                if not self.bids:
                    break  # no bids to match against
                best_bid_price, best_bid_level = self.bids.peekitem(-1)
                if order.price > best_bid_price:
                    break  # incoming sell doesn't cross the book
                # Match against the best bid level
                trade_qty = min(order.quantity, best_bid_level.peek_front().quantity)
                resting_order = best_bid_level.peek_front()
                best_bid_level.fill_front(trade_qty)
                if resting_order.quantity == 0:
                    del self.order_locations[resting_order.order_id]
                order.quantity -= trade_qty
                if best_bid_level.is_empty():
                    del self.bids[best_bid_price]
                trade_records.append(Trade(
                    price=best_bid_price,
                    quantity=trade_qty,
                    buy_order_id=resting_order.order_id,
                    sell_order_id=order.order_id  
                ))
        # If any quantity remains unfilled, rest it on the book on its own side, creating a new PriceLevel if needed.
        if order.quantity > 0:
            if order.side == order_side.BUY:
                if order.price not in self.bids:
                    self.bids[order.price] = PriceLevel(order.price)
                self.bids[order.price].add(order)
            else:  # SELL
                if order.price not in self.asks:
                    self.asks[order.price] = PriceLevel(order.price)
                self.asks[order.price].add(order)
            self.order_locations[order.order_id] = (order.side, order.price)

        return trade_records, order if order.quantity > 0 else None


    def cancel_order(self, order_id):
        """
        Cancel a resting order by id. Use order_locations for O(1) lookup
        of which side/price it's on, remove it from the relevant
        PriceLevel, clean up order_locations, and remove the PriceLevel
        from the book entirely if it's now empty.
        """
        if order_id not in self.order_locations:
            return  # Order not found, nothing to cancel

        side, price = self.order_locations[order_id]
        if side == order_side.BUY:
            price_level = self.bids.get(price)
        else:  # SELL
            price_level = self.asks.get(price)

        if price_level:
            price_level.remove_order(order_id)
            if price_level.is_empty():
                if side == order_side.BUY:
                    del self.bids[price]
                else:
                    del self.asks[price]

        del self.order_locations[order_id]

    def best_bid(self):
        """Return the highest resting bid price, or None if there are no bids."""
        return self.bids.peekitem(-1)[0] if self.bids else None

    def best_ask(self):
        """Return the lowest resting ask price, or None if there are no asks."""
        return self.asks.peekitem(0)[0] if self.asks else None

    def get_spread(self):
        """
        Return best_ask - best_bid, or None if either side is empty.
        """
        best_bid = self.best_bid()
        best_ask = self.best_ask()
        return best_ask - best_bid if best_bid is not None and best_ask is not None else None

    def mid_price(self):
        """
        Return (best_bid + best_ask) / 2, or None if either side is empty.
        """
        best_bid = self.best_bid()
        best_ask = self.best_ask()
        return (best_bid + best_ask) / 2 if best_bid is not None and best_ask is not None else None

    def get_depth(self, levels=5):
        """
        Return a snapshot of resting depth on both sides, e.g.
        {'bids': [(price, total_quantity), ...], 'asks': [(price, total_quantity), ...]}
        with bids ordered best-to-worst (highest price first) and asks
        ordered best-to-worst (lowest price first), up to `levels` price
        levels per side.
        """
        bid_depth = [(price, level.total_quantity) for price, level in reversed(self.bids.items())][:levels]
        ask_depth = [(price, level.total_quantity) for price, level in self.asks.items()][:levels]
        return {'bids': bid_depth, 'asks': ask_depth}

    def __repr__(self):
        return f"OrderBook(best_bid={self.best_bid()!r}, best_ask={self.best_ask()!r})"