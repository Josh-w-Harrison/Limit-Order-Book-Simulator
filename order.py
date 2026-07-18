from dataclasses import dataclass, field
from enum import Enum
from itertools import count

class order_side(Enum):
    BUY = "BUY"
    SELL = "SELL"


# Currently only supports LIMIT but I will add MARKET and IOC in the future
class order_type(Enum):
    LIMIT = "LIMIT"    # rests on the book if not fully matched
    MARKET = "MARKET"  # matches immediately at best available price(s), never rests
    IOC = "IOC"        # Immediate-Or-Cancel: matches what it can right now,
                        # unfilled remainder is dropped, never rests

class Order:
    _id_counter = count(1)

    def __init__(self, side, type = order_type.LIMIT, price = 0.0, quantity = 0):
        self.side = side
        self.type = type
        self.price = price
        self.quantity = quantity
        self.order_id = next(Order._id_counter)

    def __repr__(self):
        return f"Order(side={self.side!r}, type={self.type!r}, price={self.price!r}, quantity={self.quantity!r})"