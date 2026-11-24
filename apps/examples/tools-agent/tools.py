"""Tools: plain functions with type hints and a docstring. The docstring is
what the model reads to decide when to call a tool, so make it precise.
Replace the examples with calls to your own systems (HTTP APIs, databases...)."""

from aiapp import app

STOCK = {"espresso-machine": 4, "grinder": 0, "kettle": 12}


@app.tool
def check_stock(product: str) -> dict:
    """How many units of a product are in stock. Products: espresso-machine, grinder, kettle."""
    if product not in STOCK:
        return {"error": f"unknown product {product!r}"}
    return {"product": product, "in_stock": STOCK[product]}


@app.tool
def delivery_days(country: str) -> int:
    """Delivery time in working days for an ISO country code such as FR or US."""
    return {"FR": 2, "DE": 3, "US": 7}.get(country.upper(), 10)
