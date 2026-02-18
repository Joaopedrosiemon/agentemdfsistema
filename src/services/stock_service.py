"""Stock checking and availability service."""

from src.database import queries
from config.settings import DEFAULT_MIN_STOCK


def check_availability(product_id: int) -> dict:
    """Check stock availability for a product."""
    row = queries.get_product_with_stock(product_id)
    if not row:
        return {"found": False, "error": "Produto nao encontrado"}

    product = dict(row)
    qty_available = product.get("quantity_available") or 0
    qty_reserved = product.get("quantity_reserved") or 0
    net = qty_available - qty_reserved
    minimum = product.get("minimum_stock") or 0

    return {
        "found": True,
        "product_id": product["id"],
        "product_code": product["product_code"],
        "product_name": product["product_name"],
        "brand": product["brand"],
        "quantity_available": qty_available,
        "quantity_reserved": qty_reserved,
        "net_available": net,
        "in_stock": net >= DEFAULT_MIN_STOCK,
        "is_low_stock": 0 < net <= minimum,
        "minimum_stock": minimum,
        "location": product.get("location", "principal"),
        "unit": product.get("unit", "chapa"),
    }


def filter_available_products(product_ids: list[int], min_qty: float = None) -> list[int]:
    """Filter a list of product IDs to only those with stock."""
    if min_qty is None:
        min_qty = DEFAULT_MIN_STOCK
    available = []
    for pid in product_ids:
        stock = queries.get_stock_by_product_id(pid)
        if stock and (stock["quantity_available"] - stock["quantity_reserved"]) >= min_qty:
            available.append(pid)
    return available
