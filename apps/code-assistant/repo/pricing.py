"""Order pricing for the sample shop."""

TAX_RATE = 0.2


def subtotal(items):
    """Sum of price * quantity for the order's items."""
    return sum(i["price"] * i["quantity"] for i in items)


def total(items, coupon=None):
    """Subtotal minus the coupon's discount, plus tax."""
    amount = subtotal(items)
    if coupon == "WELCOME10":
        amount *= 0.9
    return round(amount * (1 + TAX_RATE), 2)
