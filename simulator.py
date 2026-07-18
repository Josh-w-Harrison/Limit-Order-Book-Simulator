class Simulator:
    def __init__(self, order_book, market_data_generator):
        self.order_book = order_book
        self.market_data_generator = market_data_generator

    def step(self):
        """
        Pull one order from the market data generator, submit it to the
        order book, record whatever metrics/history are needed, and
        return whatever a single step's caller (run(), or later
        backtest.py) needs to see.
        """
        next_order = self.market_data_generator.next_order()
        fills, remaining = self.order_book.add_order(next_order)
        return fills, remaining

    def run(self, n_steps):
        """
        Call step() n_steps times and return the accumulated history.
        """
        history = []
        for _ in range(n_steps):
            fills, remaining = self.step()
            history.append({
                'reference_price': self.market_data_generator.get_reference_price(),
                'best_bid': self.order_book.best_bid(),
                'best_ask': self.order_book.best_ask(),
                'mid_price': self.order_book.mid_price(),
                'spread': self.order_book.get_spread(),
                'fills': fills,
                'remaining_order_id': remaining.order_id if remaining is not None else None,
                'remaining_qty': remaining.quantity if remaining is not None else 0,
                'depth_snapshot': self.order_book.get_depth()
            })
        return history
