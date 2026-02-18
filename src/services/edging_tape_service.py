"""Edging tape matching and compatibility service."""

from src.database import queries


def find_compatible(product_id: int) -> list[dict]:
    """
    Find compatible edging tapes for a product.
    Falls back to color family matching if no official compatibility exists.
    """
    # Strategy 1: Official compatibility
    rows = queries.get_compatible_tapes(product_id)
    if rows:
        return [dict(row) for row in rows]

    # Strategy 2: Fallback — match by color family
    product = queries.get_product_by_id(product_id)
    if not product or not product.get("color_family"):
        return []

    tapes = queries.get_tapes_by_color_family(product["color_family"])
    results = []
    for tape in tapes:
        result = dict(tape)
        result["compatibility_type"] = "alternative"
        results.append(result)

    # Prioritize same brand
    results.sort(key=lambda x: (0 if x["brand"] == product["brand"] else 1))
    return results


def find_tape_for_substitute(
    original_product_id: int,
    substitute_product_id: int,
) -> list[dict]:
    """
    Find edging tape for a substitute product.
    Priority: substitute's own tape > original's tape > equivalents > color match.
    """
    # Try substitute's own tapes first
    sub_tapes = find_compatible(substitute_product_id)
    if sub_tapes:
        return sub_tapes

    # Try original product's tapes
    orig_tapes = find_compatible(original_product_id)
    if orig_tapes:
        # Check if any tape equivalents exist
        for tape in orig_tapes:
            equivalents = queries.get_tape_equivalents(tape["id"])
            if equivalents:
                return [dict(eq) for eq in equivalents]

    return orig_tapes
