"""Product search service with fuzzy matching."""

import re
from rapidfuzz import fuzz
from src.database import queries
from src.utils.text_processing import normalize_text
from config.settings import FUZZY_MATCH_THRESHOLD, MAX_SEARCH_RESULTS, PRIMARY_LOCATION

# Cache for fuzzy matching (avoids reloading + re-normalizing every search)
_fuzzy_cache: list[dict] | None = None


def search(query: str) -> list[dict]:
    """
    Multi-strategy product search.
    Returns list of products with match_score and match_type.
    """
    query = query.strip()
    if not query:
        return []

    required_thickness = _extract_thickness_mm(query)
    query_for_match = _normalize_query_for_search(query)

    results = []
    seen_ids = set()

    # Strategy 1: Exact code match (instant)
    product = queries.get_product_by_code(query.upper())
    if product:
        result = dict(product)
        result["match_score"] = 1.0
        result["match_type"] = "exact_code"
        _enrich_with_stock(result)
        return [result]

    # Strategy 2: SQL LIKE search (fast, uses indexes)
    sql_limit = 100 if required_thickness is not None else 20
    sql_results = queries.search_products_by_name(query_for_match, limit=sql_limit)
    exact_name_match = False
    if sql_results:
        for row in sql_results:
            result = dict(row)
            result["match_score"] = _compute_match_score(query_for_match, result)
            result["match_type"] = "name_match"
            _enrich_with_stock(result)
            results.append(result)
            seen_ids.add(result["id"])
            if normalize_text(result["product_name"]) == normalize_text(query_for_match):
                exact_name_match = True

    # Strategy 3: Fuzzy matching with cache (only if SQL found < 3 results
    # and no exact name match was found)
    if len(results) < 3 and not exact_name_match:
        normalized_query = normalize_text(query_for_match)
        fuzzy_items = _get_fuzzy_cache()

        fuzzy_results = []
        for item in fuzzy_items:
            if item["id"] in seen_ids:
                continue

            score = _fuzzy_score_cached(normalized_query, item)
            if score >= FUZZY_MATCH_THRESHOLD:
                fuzzy_results.append((score, item))

        # Sort and take top results
        fuzzy_results.sort(key=lambda x: x[0], reverse=True)
        for score, item in fuzzy_results[:MAX_SEARCH_RESULTS]:
            product = dict(item["row"])
            product["match_score"] = score
            product["match_type"] = "fuzzy"
            _enrich_with_stock(product)
            results.append(product)

    results.sort(key=lambda x: x["match_score"], reverse=True)

    if required_thickness is not None:
        matched = []
        for r in results:
            thickness = r.get("thickness_mm")
            r["requested_thickness_mm"] = required_thickness
            if thickness is None:
                r["thickness_match"] = False
                continue
            if abs(float(thickness) - required_thickness) <= 0.1:
                r["thickness_match"] = True
                matched.append(r)
            else:
                r["thickness_match"] = False
        if matched:
            return matched[:MAX_SEARCH_RESULTS]
    return results[:MAX_SEARCH_RESULTS]


def invalidate_cache():
    """Clear the fuzzy search cache (call after data imports)."""
    global _fuzzy_cache
    _fuzzy_cache = None


def _get_fuzzy_cache() -> list[dict]:
    """Get or build the pre-processed fuzzy search cache."""
    global _fuzzy_cache
    if _fuzzy_cache is None:
        all_products = queries.get_all_active_products()
        _fuzzy_cache = []
        for row in all_products:
            product = dict(row)
            _fuzzy_cache.append({
                "id": product["id"],
                "norm_name": normalize_text(product["product_name"]),
                "norm_brand_name": normalize_text(
                    f"{product['brand']} {product['product_name']}"
                ),
                "norm_code": normalize_text(product["product_code"]),
                "row": product,
            })
    return _fuzzy_cache


def _compute_match_score(query: str, product: dict) -> float:
    """Compute relevance score for a SQL LIKE match."""
    norm_query = normalize_text(query)
    name_score = fuzz.token_sort_ratio(
        norm_query, normalize_text(product["product_name"])
    ) / 100
    brand_score = fuzz.token_sort_ratio(
        norm_query, normalize_text(product["brand"])
    ) / 100
    combined = normalize_text(f"{product['brand']} {product['product_name']}")
    combined_score = fuzz.token_sort_ratio(norm_query, combined) / 100
    return max(name_score, brand_score, combined_score)


def _fuzzy_score_cached(normalized_query: str, item: dict) -> float:
    """Compute fuzzy match score using pre-normalized data (faster)."""
    name_score = fuzz.token_sort_ratio(normalized_query, item["norm_name"]) / 100
    combined_score = fuzz.token_sort_ratio(
        normalized_query, item["norm_brand_name"]
    ) / 100
    code_score = fuzz.ratio(normalized_query, item["norm_code"]) / 100
    return max(name_score, combined_score, code_score)


def _enrich_with_stock(product: dict):
    """Add stock information to a product dict."""
    stock = queries.get_stock_by_product_id(
        product["id"], location=PRIMARY_LOCATION
    )
    if stock:
        product["quantity_available"] = stock["quantity_available"]
        product["quantity_reserved"] = stock["quantity_reserved"]
        product["location"] = stock["location"]
        product["in_stock"] = (
            stock["quantity_available"] - stock["quantity_reserved"]
        ) > 0
    else:
        product["quantity_available"] = 0
        product["quantity_reserved"] = 0
        product["location"] = PRIMARY_LOCATION
        product["in_stock"] = False


def _extract_thickness_mm(text: str) -> float | None:
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*mm", text, re.IGNORECASE)
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", "."))
    except Exception:
        return None


def _normalize_query_for_search(query: str) -> str:
    """Remove thickness/material tokens to improve name matching."""
    q = query
    q = re.sub(r"\b\d+(?:[.,]\d+)?\s*mm\b", "", q, flags=re.IGNORECASE)
    q = re.sub(r"\b(mdf|mdp|bp|pvc|hdf)\b", "", q, flags=re.IGNORECASE)
    q = re.sub(r"\s+", " ", q).strip()
    return q or query
