"""Edging tape matching and compatibility service."""

from rapidfuzz import fuzz

from src.database import queries
from src.utils.text_processing import normalize_text
from config.settings import TAPE_METERS_PER_ROLL


def find_compatible(product_id: int) -> list[dict]:
    """
    Find compatible edging tapes for a product.
    Falls back to name-based matching if no official compatibility exists.
    """
    # Strategy 1: Official compatibility
    rows = queries.get_compatible_tapes(product_id)
    if rows:
        return _decorate_tapes([dict(row) for row in rows])

    # Strategy 2: Fallback - match by name
    product = queries.get_product_by_id(product_id)
    if not product:
        return []

    candidates = queries.search_tapes_by_name(product["product_name"], limit=50)
    if not candidates:
        terms = [t for t in normalize_text(product["product_name"]).split() if len(t) > 2]
        seen = {}
        for term in terms:
            for row in queries.search_tapes_by_name(term, limit=50):
                seen[row["id"]] = row
        candidates = list(seen.values())
    if not candidates:
        return []

    results = []
    for tape_row in candidates:
        tape = dict(tape_row)
        tape["compatibility_type"] = "name_match"
        tape["match_score"] = _compute_match_score(product["product_name"], tape)
        results.append(tape)

    # Filter weak matches
    results = [t for t in results if t.get("match_score", 0) >= 0.5]
    if not results:
        return []

    # Prioritize in-stock, then brand match, then score
    results = _decorate_tapes(results)
    results.sort(
        key=lambda x: (
            x.get("in_stock", False),
            x.get("brand") == product["brand"],
            x.get("match_score", 0),
        ),
        reverse=True,
    )
    return results[:10]


def find_tape_for_substitute(
    original_product_id: int,
    substitute_product_id: int,
) -> list[dict]:
    """
    Find edging tape for a substitute product.
    Priority: substitute's own tape > original's tape > equivalents > name match.
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
                return _decorate_tapes([dict(eq) for eq in equivalents])

    return orig_tapes


def _compute_match_score(product_name: str, tape: dict) -> float:
    """Compute a fuzzy match score between product and tape names."""
    norm_query = normalize_text(product_name)
    name_score = (
        fuzz.token_sort_ratio(norm_query, normalize_text(tape.get("tape_name", ""))) / 100
    )
    brand_score = (
        fuzz.token_sort_ratio(norm_query, normalize_text(tape.get("brand", ""))) / 100
    )
    combined = normalize_text(f"{tape.get('brand', '')} {tape.get('tape_name', '')}")
    combined_score = fuzz.token_sort_ratio(norm_query, combined) / 100
    return max(name_score, brand_score, combined_score)


def _decorate_tapes(tapes: list[dict]) -> list[dict]:
    """Attach stock flags for tape results."""
    for tape in tapes:
        qty_meters = tape.get("quantity_available_meters")
        try:
            if qty_meters is None:
                qty_meters = tape.get("quantity_available")
            qty_meters = float(qty_meters) if qty_meters is not None else 0
        except Exception:
            qty_meters = 0

        if TAPE_METERS_PER_ROLL > 0:
            qty_rolls = qty_meters / TAPE_METERS_PER_ROLL
        else:
            qty_rolls = qty_meters

        tape["quantity_available_meters"] = qty_meters
        tape["quantity_available"] = qty_rolls
        tape["unit"] = "rolos"
        tape["in_stock"] = qty_meters > 0
    return tapes
