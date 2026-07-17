from itertools import count


class Trade:
    """
    A single match between an incoming order and a resting order.

    Design questions to think through while implementing:
      - trade_id: follow the same pattern as Order.order_id -- a single
        shared, strictly-increasing itertools.count class attribute. Why
        does a trade need its own id at all, separate from the two order
        ids involved? (Think about what you'd query by later: "give me
        all trades in sequence order" vs "give me all trades involving
        order X".)
      - price: a match happens at the resting order's price, not the
        incoming order's price (the resting order was there first and its
        price is what the aggressor agreed to cross). Make sure whatever
        code constructs a Trade passes the resting order's price, not
        order.price of the incoming order.
      - buy_order_id / sell_order_id: store ids, not references to the
        Order objects themselves. Why might holding a live reference to a
        mutable Order (whose .quantity keeps changing) be the wrong thing
        for a historical trade record to point to?
      - Do you need a quantity field? (Yes -- the fill size for this
        specific match, which is generally different from either order's
        original quantity.)
    """

    _id_counter = count(1)

    def __init__(self, price, quantity, buy_order_id, sell_order_id):
        self.trade_id = next(Trade._id_counter)
        self.price = price
        self.quantity = quantity
        self.buy_order_id = buy_order_id
        self.sell_order_id = sell_order_id

    def __repr__(self):
        return (f"Trade(trade_id={self.trade_id!r}, price={self.price!r}, "
                f"quantity={self.quantity!r}, buy_order_id={self.buy_order_id!r}, "
                f"sell_order_id={self.sell_order_id!r})")