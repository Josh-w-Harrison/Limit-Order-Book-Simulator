from sortedcontainers import SortedDict

from order import order_side
from price_level import PriceLevel
from trade import Trade

class OrderBook:
    def __init__(self):
        self.bids = SortedDict()
        self.asks = SortedDict()
        self.order_locations = {}

    def add_order(self, order):
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
        return self.bids.peekitem(-1)[0] if self.bids else None

    def best_ask(self):
        return self.asks.peekitem(0)[0] if self.asks else None

    def get_spread(self):
        best_bid = self.best_bid()
        best_ask = self.best_ask()
        return best_ask - best_bid if best_bid is not None and best_ask is not None else None

    def mid_price(self):
        best_bid = self.best_bid()
        best_ask = self.best_ask()
        return (best_bid + best_ask) / 2 if best_bid is not None and best_ask is not None else None

    def get_depth(self, levels=5):
        bid_depth = [(price, level.total_quantity) for price, level in reversed(self.bids.items())][:levels]
        ask_depth = [(price, level.total_quantity) for price, level in self.asks.items()][:levels]
        return {'bids': bid_depth, 'asks': ask_depth}

    def __repr__(self):
        return f"OrderBook(best_bid={self.best_bid()!r}, best_ask={self.best_ask()!r})"