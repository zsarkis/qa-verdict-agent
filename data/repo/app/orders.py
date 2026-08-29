"""Order pricing and fulfilment logic."""

from app.models import Order

FLAT_SHIPPING = 5.00
FREE_SHIPPING_THRESHOLD = 100.00


def subtotal(order: Order) -> float:
    return sum(item.unit_price * item.quantity for item in order.items)


def shipping_fee(order: Order) -> float:
    if subtotal(order) >= FREE_SHIPPING_THRESHOLD:
        return 0.00
    return FLAT_SHIPPING


def order_total(order: Order) -> float:
    return subtotal(order) + shipping_fee(order)
