from order import Order, order_side


class MarketMaker:
    def __init__(self, half_spread, skew_coefficient, quote_size):
        self.half_spread = half_spread
        self.skew_coefficient = skew_coefficient
        self.quote_size = quote_size
        self.inventory = 0
        self.reference_price = None  # Own fair-value estimate; bootstrapped then trade-print-driven, see class docstring
        self.bid_order_id = None
        self.ask_order_id = None
        self.bid_remaining = 0  # Quantity still resting on our own bid/ask -- Trade has no remaining_quantity field, so we track this ourselves
        self.ask_remaining = 0
        self.cash = 0  # Track cash for PnL calculations
        self.history = []  # One snapshot per on_tick call -- {inventory, cash, reference_price, bid_price, ask_price}, for plotting/inspection

    def on_fills(self, fills):
        for trade in fills:
            if trade.buy_order_id == self.bid_order_id:
                self.inventory += trade.quantity  # Bought, inventory increases
                self.cash -= trade.quantity * trade.price  # Update cash for realized PnL
                self.bid_remaining -= trade.quantity
                if self.bid_remaining <= 0:
                    self.bid_order_id = None  # Fully filled, no longer resting
            elif trade.sell_order_id == self.ask_order_id:
                self.inventory -= trade.quantity  # Sold, inventory decreases
                self.cash += trade.quantity * trade.price  # Update cash for realized PnL
                self.ask_remaining -= trade.quantity
                if self.ask_remaining <= 0:
                    self.ask_order_id = None  # Fully filled, no longer resting

        self.reference_price = fills[-1].price if fills else self.reference_price  # Update reference price from last trade print

    def on_tick(self, order_book):
        if self.reference_price is None:
            self.reference_price = order_book.mid_price()  # Bootstrap on first tick
        if self.reference_price is None:
            self.history.append({
                'inventory': self.inventory, 'cash': self.cash,
                'reference_price': None, 'bid_price': None, 'ask_price': None,
            })
            return

        if self.bid_order_id is not None:
            order_book.cancel_order(self.bid_order_id)
            self.bid_order_id = None
        if self.ask_order_id is not None:
            order_book.cancel_order(self.ask_order_id)
            self.ask_order_id = None

        skewed_mid = self.reference_price - self.skew_coefficient * self.inventory
        bid_price = skewed_mid - self.half_spread
        ask_price = skewed_mid + self.half_spread

        # Clamp: never submit a quote that would immediately cross the book and trade against other resting flow
        best_bid = order_book.best_bid()
        best_ask = order_book.best_ask()
        would_cross_bid = best_ask is not None and bid_price >= best_ask
        would_cross_ask = best_bid is not None and ask_price <= best_bid

        # Place new orders
        if would_cross_bid:
            self.bid_order_id = None
            self.bid_remaining = 0
        else:
            _, bid_remaining_order = order_book.add_order(Order(price=bid_price, quantity=self.quote_size, side=order_side.BUY))
            self.bid_order_id = bid_remaining_order.order_id if bid_remaining_order is not None else None
            self.bid_remaining = bid_remaining_order.quantity if bid_remaining_order is not None else 0

        if would_cross_ask:
            self.ask_order_id = None
            self.ask_remaining = 0
        else:
            _, ask_remaining_order = order_book.add_order(Order(price=ask_price, quantity=self.quote_size, side=order_side.SELL))
            self.ask_order_id = ask_remaining_order.order_id if ask_remaining_order is not None else None
            self.ask_remaining = ask_remaining_order.quantity if ask_remaining_order is not None else 0

        self.history.append({
            'inventory': self.inventory,
            'cash': self.cash,
            'reference_price': self.reference_price,
            'bid_price': None if would_cross_bid else bid_price,
            'ask_price': None if would_cross_ask else ask_price,
        })