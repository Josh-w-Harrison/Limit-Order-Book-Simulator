from collections import deque


class PriceLevel:
    def __init__(self, price):
        self.price = price
        self.orders = deque()
        self.total_quantity = 0

    def add(self, order):
        self.orders.append(order)
        self.total_quantity += order.quantity

    def peek_front(self):
        return self.orders[0] if self.orders else None

    def pop_front(self):
        order = self.orders.popleft()
        self.total_quantity -= order.quantity
        return order
     
    def fill_front(self, quantity):
        if not self.orders:
            raise ValueError("Cannot fill front order: price level is empty")
        
        front_order = self.orders[0]
        if quantity > front_order.quantity:
            raise ValueError(f"Cannot fill {quantity} units: only {front_order.quantity} available at front order")
        
        front_order.quantity -= quantity
        self.total_quantity -= quantity
        
        if front_order.quantity == 0:
            self.orders.popleft()

    def remove_order(self, id):
        for i, o in enumerate(self.orders):
            if o.order_id == id:
                self.total_quantity -= o.quantity
                del self.orders[i]
                break
        else:
            raise ValueError(f"Order {id} not found in price level {self.price}")

    def is_empty(self):
        return len(self.orders) == 0

    def __repr__(self):
        return f"PriceLevel(price={self.price!r}, total_quantity={self.total_quantity!r}, n_orders={len(self.orders)!r})"
