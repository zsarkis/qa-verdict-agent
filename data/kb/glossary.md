# Orderly Domain Glossary

- **Order** — a customer purchase; lifecycle `open → fulfilled`, or `open → archived` for
  stale orders.
- **Line item** — one SKU within an order, with unit price and quantity.
- **SKU** — stock-keeping unit identifier; non-empty, no spaces.
- **Subtotal** — sum of `unit_price × quantity` across line items, before shipping,
  discounts, or tax.
- **Stale order** — an open order past the retention cutoff and subject to archival under
  the ops retention policy (the policy itself is owned by ops; engineering does not define
  the cutoff).
- **Archived order** — excluded from default listings; retained for audit.
- **Promo code** — customer-entered code granting a percentage off the subtotal.
- **Bulk order** — informal term for high-item-count orders; thresholds are defined
  per-feature in the relevant AC, not globally.
