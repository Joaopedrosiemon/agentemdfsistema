"""Product search service with fuzzy matching."""

from rapidfuzz import fuzz
from src.database import queries
from src.utils.text_processing import normalize_text
from config.settings import FUZZY_MATCH_THRESHOLD, MAX_SEARCH_RESULTS

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
    sql_results = queries.search_products_by_name(query, limit=20)
    if sql_results:
        for row in sql_results:
            result = dict(row)
            result["match_score"] = _compute_match_score(query, result)
            result["match_type"] = "name_match"
            _enrich_with_stock(result)
            results.append(result)
            seen_ids.add(result["id"])

    # Strategy 3: Fuzzy matching with cache (only if SQL found < 3 results)
    if len(results) < 3:
        normalized_query = normalize_text(query)
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
    stock = queries.get_stock_by_product_id(product["id"])
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
        product["location"] = None
        product["in_stock"] = False
