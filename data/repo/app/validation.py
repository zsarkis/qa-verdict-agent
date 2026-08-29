"""Input validation helpers."""


def validate_quantity(quantity: int) -> None:
    if quantity <= 0:
        raise ValueError("quantity must be a positive integer")


def validate_sku(sku: str) -> None:
    if not sku or " " in sku:
        raise ValueError("sku must be non-empty and contain no spaces")
