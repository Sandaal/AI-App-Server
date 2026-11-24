"""Tools the agent can use. Replace these examples with calls to your own systems."""

from aiapp import app

ORDERS = {
    "A-1001": {"customer": 1042, "item": "Espresso machine", "total": 249.0, "status": "lost in transit"},
    "A-1002": {"customer": 1042, "item": "Coffee grinder", "total": 89.0, "status": "delivered"},
}


@app.tool
def lookup_order(order_id: str) -> dict:
    """Look up an order by id (e.g. A-1001): item, total, customer and shipping status."""
    return ORDERS.get(order_id, {"error": "no such order"})


@app.tool
def lookup_customer(customer_id: int) -> dict:
    """Look up a customer by numeric id: name and contact email."""
    return {"customer_id": customer_id, "name": "Ada Lovelace", "email": "ada@example.com"}


@app.tool
def refund_order(order_id: str, reason: str) -> str:
    """Refund an order in full. Needs a person's approval first (see ai-app.yaml)."""
    order = ORDERS.get(order_id)
    if not order:
        return "no such order"
    return f"Refunded {order['total']:.2f} for {order_id} ({reason})."
