from collections import deque
import numpy as np

class Simulator:
    def __init__(self, order_book, market_data_generator, max_age = 10, seed=None):
        self.order_book = order_book
        self.market_data_generator = market_data_generator
        self.max_age = max_age
        self.trade_ages = deque()
        self._tick_count = 0
        self._rng = np.random.default_rng(seed)
        self._poisson_lambda = 3.0  # Default lambda for Poisson distribution

    def step(self):
        next_order = self.market_data_generator.next_order()
        fills, remaining = self.order_book.add_order(next_order)

        # Record the age of each trade
        if remaining is not None:
            self.trade_ages.append((remaining.order_id, self._tick_count))
        
        

        return fills, remaining

    def run(self, n_ticks):
        history = []
        for _ in range(n_ticks):
            self._tick_count += 1
            self.market_data_generator.advance_tick()
            K = self._rng.poisson(self._poisson_lambda) # Sample the number of orders to generate from a Poisson distribution

            for _ in range(K):
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
                    'depth_snapshot': self.order_book.get_depth(),
                    'tick': self._tick_count
                })

            # Remove old trades that exceed the maximum age
            while self.trade_ages and self.trade_ages[0][1] <= self._tick_count - self.max_age:
                order_id, _ = self.trade_ages.popleft()
                self.order_book.cancel_order(order_id)

        return history
