"""In-memory order store. A real deployment would use a database."""

from app.models import Order

ORDERS: dict[str, Order] = {}
