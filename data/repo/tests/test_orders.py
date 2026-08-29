from app.models import Customer, LineItem, Order
from app.orders import order_total, shipping_fee, subtotal


def make_order(*items):
    customer = Customer(id="c1", name="Test Customer", email="test@example.com")
    return Order(id="o1", customer=customer, items=list(items))


def test_subtotal_sums_line_items():
    order = make_order(
        LineItem("SKU-1", "Widget", 10.00, 2),
        LineItem("SKU-2", "Gadget", 5.00, 1),
    )
    assert subtotal(order) == 25.00


def test_shipping_is_flat_below_threshold():
    order = make_order(LineItem("SKU-1", "Widget", 10.00, 1))
    assert shipping_fee(order) == 5.00


def test_shipping_free_at_threshold():
    order = make_order(LineItem("SKU-1", "Widget", 100.00, 1))
    assert shipping_fee(order) == 0.00


def test_order_total_includes_shipping():
    order = make_order(LineItem("SKU-1", "Widget", 10.00, 1))
    assert order_total(order) == 15.00
