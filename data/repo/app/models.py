"""Domain models for Orderly, a small order-management service."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Customer:
    id: str
    name: str
    email: str


@dataclass
class LineItem:
    sku: str
    description: str
    unit_price: float
    quantity: int


@dataclass
class Order:
    id: str
    customer: Customer
    items: list[LineItem] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: str = "open"  # open | fulfilled | archived

    @property
    def item_count(self) -> int:
        return sum(item.quantity for item in self.items)
