"""Stock checking and availability service."""

from src.database import queries
from config.settings import DEFAULT_MIN_STOCK, PRIMARY_LOCATION


def check_availability(product_id: int, include_other_locations: bool = False) -> dict:
    """Check stock availability for a product."""
    row = queries.get_product_with_stock(product_id, location=PRIMARY_LOCATION)
    if not row:
        return {"found": False, "error": "Produto nao encontrado"}

    product = dict(row)
    qty_available = product.get("quantity_available") or 0
    qty_reserved = product.get("quantity_reserved") or 0
    net = qty_available - qty_reserved
    minimum = product.get("minimum_stock") or 0

    response = {
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
        "location": product.get("location", PRIMARY_LOCATION),
        "unit": product.get("unit", "chapa"),
    }
    if include_other_locations:
        other_rows = queries.get_stock_other_locations(
            product_id, primary_location=PRIMARY_LOCATION
        )
        other_locations = []
        seen_locations = set()
        for row in other_rows:
            row_dict = dict(row)
            location = row_dict.get("location")
            if location in seen_locations:
                continue
            qty_available = row_dict.get("quantity_available") or 0
            qty_reserved = row_dict.get("quantity_reserved") or 0
            net = qty_available - qty_reserved
            if net < DEFAULT_MIN_STOCK:
                continue
            other_locations.append(
                {
                    "location": location,
                    "quantity_available": qty_available,
                    "quantity_reserved": qty_reserved,
                    "net_available": net,
                    "unit": row_dict.get("unit", "chapa"),
                    "last_updated": row_dict.get("last_updated"),
                }
            )
            seen_locations.add(location)
        response["other_locations"] = other_locations
    return response


def filter_available_products(product_ids: list[int], min_qty: float = None) -> list[int]:
    """Filter a list of product IDs to only those with stock."""
    if min_qty is None:
        min_qty = DEFAULT_MIN_STOCK
    available = []
    for pid in product_ids:
        stock = queries.get_stock_by_product_id(pid, location=PRIMARY_LOCATION)
        if stock and (stock["quantity_available"] - stock["quantity_reserved"]) >= min_qty:
            available.append(pid)
    return available
