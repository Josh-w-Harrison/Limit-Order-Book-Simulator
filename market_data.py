import random
from dataclasses import dataclass

import pandas as pd

from order import Order, order_side, market_event_type


@dataclass
class MarketEvent:
    """
    A single unit of market activity handed from a generator to
    Simulator.step(). type determines which fields are populated:
      SUBMIT -> order is set (a brand new Order to run through add_order)
      CANCEL -> order_id is set (the internal mapped id, to run through cancel_order)
      REDUCE -> order_id and quantity are set (to run through reduce_order)
    """
    type: market_event_type
    order: Order = None
    order_id: int = None
    quantity: int = None


class MarketDataGenerator:
    def __init__(self, initial_price, seed=None):
        self._reference_price = initial_price
        self._rng = random.Random(seed)
        self._tick_count = 0

    def next_event(self, mean_quantity=10):
        # Generate order side
        side = order_side.BUY if self._rng.random() < 0.5 else order_side.SELL
        if side == order_side.BUY:
            price_offset = self._rng.normalvariate(-0.5, 0.2)
        else:
            price_offset = self._rng.normalvariate(0.5, 0.2)

        # Generate order price offset from reference price
        order_price = max(0.01, self._reference_price + price_offset)  # Ensure positive price

        # Generate order quantity
        order_quantity = max(1, int(self._rng.expovariate(1/mean_quantity)))  # Exponential distribution with mean mean_quantity

        order = Order(price=order_price, quantity=order_quantity, side=side)
        return MarketEvent(type=market_event_type.SUBMIT, order=order)

    def advance_tick(self, volatility=0.5):
        # Random walk the reference price
        self._reference_price += self._rng.normalvariate(0, volatility)
        self._tick_count += 1

    def get_reference_price(self):
        return self._reference_price

    def get_last_event_time(self):
        return self._tick_count


class HistoricalMarketDataGenerator:
    def __init__(self, csv_path, seed=None):
        self._historical_prices = pd.read_csv(csv_path)['Close'].tolist()
        self._current_index = 0
        self._reference_price = self._historical_prices[self._current_index]
        self._rng = random.Random(seed)


    def next_event(self, volatility=0.5, mean_quantity=10):
        # Generate order side
        side = order_side.BUY if self._rng.random() < 0.5 else order_side.SELL
        if side == order_side.BUY:
            price_offset = self._rng.normalvariate(-0.5, 0.2)
        else:
            price_offset = self._rng.normalvariate(0.5, 0.2)

        # Generate order price offset from reference price
        order_price = max(0.01, self._reference_price + price_offset)  # Ensure positive price

        # Generate order quantity
        order_quantity = max(1, int(self._rng.expovariate(1/mean_quantity)))  # Exponential distribution with mean mean_quantity

        order = Order(price=order_price, quantity=order_quantity, side=side)
        return MarketEvent(type=market_event_type.SUBMIT, order=order)

    def get_reference_price(self):
        return self._reference_price

    def get_last_event_time(self):
        return self._current_index

    def advance_tick(self):
        self._current_index += 1
        if 0 <= self._current_index < len(self._historical_prices):
            self._reference_price = self._historical_prices[self._current_index]


class LOBSTERMarketDataGenerator:
    def __init__(self, message_csv_path, seed=None, start_row=0, end_row=None):
        df = pd.read_csv(message_csv_path, header=None,
                          names=['Time', 'EventType', 'OrderID', 'Size', 'Price', 'Direction'])
        df = df.iloc[start_row:end_row]
        self._times = df['Time'].tolist()
        self._event_types = df['EventType'].tolist()
        self._order_ids = df['OrderID'].tolist()
        self._sizes = df['Size'].tolist()
        self._prices = df['Price'].tolist()
        self._directions = df['Direction'].tolist()
        self._n_rows = len(df)

        self._current_index = 0
        self._reference_price = None  # Will be set when first Type 4 is encountered
        self._lobster_to_internal_id = {}
        self._rng = random.Random(seed)
        self._EventType_mapping = {
            1: market_event_type.SUBMIT,
            2: market_event_type.REDUCE,
            3: market_event_type.CANCEL,
            4: market_event_type.SUBMIT,  # Aggressive order to match resting order
            5: None,  # Hidden order execution, skip
            7: None   # Trading halt, skip
        }

    def next_event(self):
        while True:
            if self._current_index >= self._n_rows:
                raise StopIteration("End of LOBSTER data reached")

            order_id = self._order_ids[self._current_index]
            type_num = self._event_types[self._current_index]
            type = self._EventType_mapping.get(type_num)

            if type is None:
                self._current_index += 1
                continue

            if type in (market_event_type.CANCEL, market_event_type.REDUCE) \
                    and order_id not in self._lobster_to_internal_id:
                self._current_index += 1
                continue

            break  # row is usable -- fall through to build the event

        if type == market_event_type.CANCEL or type == market_event_type.REDUCE:
            internal_id = self._lobster_to_internal_id[order_id]
            order_quantity = self._sizes[self._current_index]
            self._current_index += 1
            return MarketEvent(type, order_id=internal_id, quantity=order_quantity)
        elif type_num == 1:
            # For SUBMIT, we create a new Order and map the LOBSTER order ID to its internal id
            order_price = self._prices[self._current_index] / 10000.0  # Convert back to actual price
            order_quantity = self._sizes[self._current_index]
            side = order_side.BUY if self._directions[self._current_index] == 1 else order_side.SELL
            order = Order(price=order_price, quantity=order_quantity, side=side)
            self._lobster_to_internal_id[order_id] = order.order_id
            self._current_index += 1
            return MarketEvent(type, order=order)
        else: # type_num == 4, aggressive order to match resting order
            order_price = self._prices[self._current_index] / 10000.0  # Convert back to actual price
            order_quantity = self._sizes[self._current_index]
            side = order_side.SELL if self._directions[self._current_index] == 1 else order_side.BUY  # Opposite side of resting order
            order = Order(price=order_price, quantity=order_quantity, side=side)
            self._current_index += 1
            self._reference_price = order_price  # Update reference price to last trade price
            return MarketEvent(type, order=order)

    def get_reference_price(self):
        return self._reference_price

    def get_last_event_time(self):
        if self._current_index > 0:
            return self._times[self._current_index - 1]
        else:
            return None

    def advance_tick(self):
        pass  # In LOBSTER replay, we don't need to advance time; next_event() handles it based on the CSV data