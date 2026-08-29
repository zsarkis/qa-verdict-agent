"""Outbound customer notifications (stubbed transport)."""

from app.models import Order
from app.orders import order_total


def notify_order_created(order: Order) -> str:
    """Render and 'send' the order-confirmation email. Returns the body."""
    body = (
        f"Hi {order.customer.name},\n\n"
        f"Thanks for your order {order.id}. "
        f"Your total is ${order_total(order):.2f}.\n"
    )
    _send(order.customer.email, subject=f"Order {order.id} confirmed", body=body)
    return body


def _send(to: str, subject: str, body: str) -> None:
    # Transport stub: a real deployment would hand off to an email provider.
    print(f"[email to={to} subject={subject!r}]")
