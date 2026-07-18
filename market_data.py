import random
from order import Order, order_side

class MarketDataGenerator:
    def __init__(self, initial_price, seed=None):
        self._reference_price = initial_price
        self._rng = random.Random(seed)

    def next_order(self, volatility=0.5, mean_quantity=10):
        # Random walk the reference price
        self._reference_price += self._rng.normalvariate(0, volatility)

        # Generate order side
        side = order_side.BUY if self._rng.random() < 0.5 else order_side.SELL

        # Generate order price offset from reference price
        price_offset = self._rng.normalvariate(0.2, 0.5)
        order_price = max(0.01, self._reference_price + price_offset)  # Ensure positive price

        # Generate order quantity
        order_quantity = max(1, int(self._rng.expovariate(1/mean_quantity)))  # Exponential distribution with mean mean_quantity

        return Order(price=order_price, quantity=order_quantity, side=side)

    def get_reference_price(self):
        return self._reference_price    
    