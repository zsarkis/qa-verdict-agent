"""HTTP-ish handlers for Orderly.

Framework-agnostic on purpose: each handler takes a plain dict and returns
a plain dict, so handlers are trivial to test without an HTTP server.
"""

from app.models import Customer, Order
from app.orders import order_total
from app.store import ORDERS
from app.validation import validate_quantity, validate_sku


def list_orders(params: dict) -> dict:
    orders = [o for o in ORDERS.values() if o.status != "archived"]
    return {"orders": [o.id for o in orders], "count": len(orders)}


def create_order(payload: dict) -> dict:
    for item in payload.get("items", []):
        validate_sku(item["sku"])
        validate_quantity(item["quantity"])
    order = Order(id=payload["id"], customer=Customer(**payload["customer"]))
    ORDERS[order.id] = order
    return {"id": order.id, "total": order_total(order)}
