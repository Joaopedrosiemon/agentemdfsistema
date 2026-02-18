"""Direct equivalence service (Option 1) — lookup-based."""

from src.database import queries
from config.settings import DEFAULT_MIN_STOCK


def find_direct_equivalents(
    product_id: int,
    require_same_thickness: bool = True,
    only_in_stock: bool = True,
) -> list[dict]:
    """
    Find direct equivalents for a product.
    Returns list of equivalent products with stock info.
    """
    rows = queries.get_equivalents(product_id)
    if not rows:
        return []

    original = queries.get_product_by_id(product_id)
    original_thickness = original["thickness_mm"] if original else None

    results = []
    for row in rows:
        product = dict(row)
        qty_available = product.get("quantity_available") or 0
        qty_reserved = product.get("quantity_reserved") or 0
        net = qty_available - qty_reserved

        # Filter by thickness
        if require_same_thickness and original_thickness:
            if product.get("thickness_mm") and product["thickness_mm"] != original_thickness:
                continue

        # Filter by stock
        if only_in_stock and net < DEFAULT_MIN_STOCK:
            continue

        product["net_available"] = net
        product["in_stock"] = net >= DEFAULT_MIN_STOCK
        results.append(product)

    # Sort by availability (most stock first), then by confidence
    results.sort(key=lambda x: (x["net_available"], x.get("confidence", 1.0)), reverse=True)
    return results
