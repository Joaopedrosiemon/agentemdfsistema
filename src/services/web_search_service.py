"""Web search service for MDF product research via Brave Search API.

Searches the web for MDF product references and cross-references
results with the local stock database.
"""

import re

import requests as http_requests

from config.settings import BRAVE_API_KEY
from src.services import product_service

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"

# Keywords used to identify MDF product mentions in web text
MDF_KEYWORDS = [
    # Generic MDF terms
    "mdf", "melamina", "chapa", "painel",
    # Wood patterns
    "carvalho", "nogal", "nogueira", "cedro", "cedrinho", "freijo",
    "rovere", "ipanema", "itapua", "jatoba", "teca", "imbuia",
    "pinho", "maple", "cumaru", "canela", "castanho", "acacia",
    "montana", "lenho", "savana", "pecan",
    # Colors
    "branco", "cinza", "grafite", "preto", "areia", "creme",
    "neve", "titanio", "chumbo", "chocolate", "tabaco",
    # Brands
    "duratex", "eucatex", "arauco", "berneck", "guararapes",
    "fibraplac", "masisa", "sonae", "floraplac", "sudati",
    # Finishes
    "design", "matt", "silk", "nature", "lacca", "chess", "trama",
]


def is_web_search_available() -> bool:
    """Check if web search is configured and available."""
    return bool(BRAVE_API_KEY)


def search_web_and_cross_reference(
    product_name: str, brand: str = ""
) -> dict:
    """
    Search the web for MDF product references and cross-reference
    with local stock database.

    Returns dict with:
      - local_matches: products mentioned online that exist in our stock
      - web_references: raw web results for vendor to see
      - summary: human-readable summary
    """
    # Step 1: Search Brave
    web_results = _search_brave(product_name, brand)

    # Handle errors from Brave
    if web_results and isinstance(web_results[0], dict) and "error" in web_results[0]:
        return {
            "local_matches": [],
            "web_references": [],
            "summary": web_results[0]["error"],
        }
    if web_results and isinstance(web_results[0], dict) and "info" in web_results[0]:
        return {
            "local_matches": [],
            "web_references": [],
            "summary": web_results[0]["info"],
        }

    # Step 2: Extract candidate product names from web snippets
    candidates = []
    for result in web_results:
        text = f"{result.get('title', '')} {result.get('snippet', '')}"
        extracted = _extract_product_candidates(text)
        for name in extracted:
            candidates.append({"name": name, "source": result})

    # Step 3: Cross-reference with local database
    required_thickness = _extract_thickness_mm(product_name)
    local_matches = _cross_reference_with_stock(
        candidates,
        exclude_product_name=product_name,
        required_thickness_mm=required_thickness,
    )

    # Step 4: Build summary
    total_web = len(web_results)
    in_stock_count = sum(1 for m in local_matches if m.get("in_stock", False))
    total_local = len(local_matches)

    if in_stock_count > 0:
        summary = (
            f"Encontrei {total_web} referencias na web. "
            f"Desses, {in_stock_count} produto(s) similar(es) esta(ao) em nosso estoque!"
        )
    elif total_local > 0:
        summary = (
            f"Encontrei {total_web} referencias na web. "
            f"{total_local} produto(s) existe(m) em nossa base, "
            f"mas nenhum com estoque disponivel."
        )
    else:
        summary = (
            f"Encontrei {total_web} referencias na web, mas nenhum dos produtos "
            f"mencionados foi encontrado em nossa base. "
            f"Veja as referencias abaixo para consultar manualmente."
        )

    return {
        "local_matches": local_matches,
        "web_references": [
            {"title": r["title"], "snippet": r["snippet"], "url": r["url"]}
            for r in web_results
        ],
        "summary": summary,
    }


# ── Internal helpers ──────────────────────────────────────────


def _search_brave(product_name: str, brand: str = "") -> list[dict]:
    """Search Brave API for MDF product references."""
    if not BRAVE_API_KEY:
        return [{"error": "Busca web nao configurada. Configure BRAVE_API_KEY no .env."}]

    # Build search query
    query_parts = []
    if brand:
        query_parts.append(brand)
    query_parts.append(product_name)
    query_parts.append("MDF similar alternativa")
    query = " ".join(query_parts)

    try:
        response = http_requests.get(
            BRAVE_SEARCH_URL,
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": BRAVE_API_KEY,
            },
            params={
                "q": query,
                "count": 8,
                "search_lang": "pt-br",
                "country": "BR",
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        results = []
        web_results = data.get("web", {}).get("results", [])

        for item in web_results[:8]:
            title = item.get("title", "")
            snippet = item.get("description", "")
            url = item.get("url", "")

            if _is_relevant_result(title, snippet, product_name):
                results.append({
                    "title": title,
                    "snippet": snippet,
                    "url": url,
                })

        if not results:
            return [{"info": f"Nenhum resultado relevante encontrado para '{product_name}'."}]

        return results

    except http_requests.exceptions.Timeout:
        return [{"error": "Busca web demorou demais. Tente novamente."}]
    except http_requests.exceptions.HTTPError as e:
        if e.response and e.response.status_code == 429:
            return [{"error": "Limite de buscas web atingido. Tente novamente mais tarde."}]
        return [{"error": f"Erro na busca web: {e}"}]
    except Exception as e:
        return [{"error": f"Erro inesperado na busca web: {str(e)}"}]


def _extract_product_candidates(text: str) -> list[str]:
    """Extract potential MDF product name fragments from web text."""
    # Split by common separators in MDF product descriptions
    separators = (
        r'[,;.()\[\]|/\-]'
        r'|\bou\b|\bcomo\b|\bsimilar\b|\balternativa\b'
        r'|\bequivalente\b|\bsubstituto\b|\bversao\b'
    )
    fragments = re.split(separators, text, flags=re.IGNORECASE)

    candidates = []
    seen = set()

    for frag in fragments:
        frag = frag.strip()
        words = frag.split()

        # Product names are typically 2-8 words
        if len(words) < 2 or len(words) > 8:
            continue

        lower = frag.lower()

        # Must contain at least one MDF-relevant keyword
        if any(kw in lower for kw in MDF_KEYWORDS):
            # Normalize for dedup
            key = lower.strip()
            if key not in seen:
                seen.add(key)
                candidates.append(frag)

    return candidates[:15]  # Cap to avoid excessive DB queries


def _cross_reference_with_stock(
    candidates: list[dict],
    exclude_product_name: str = "",
    required_thickness_mm: float | None = None,
) -> list[dict]:
    """Cross-reference candidate product names with local database."""
    matches = {}  # product_id -> product dict (dedup)
    exclude_lower = exclude_product_name.lower().strip()

    for candidate in candidates:
        name = candidate["name"]
        source = candidate["source"]

        # Use existing product_service.search (LIKE + fuzzy + stock enrichment)
        results = product_service.search(name)

        for product in results:
            pid = product["id"]

            # Skip the original product itself
            if exclude_lower and exclude_lower in product.get("product_name", "").lower():
                continue

            # Enforce same thickness when known
            if required_thickness_mm is not None:
                thickness = product.get("thickness_mm")
                if thickness is None:
                    continue
                if abs(float(thickness) - required_thickness_mm) > 0.1:
                    continue

            # Only include if match quality is reasonable
            if product.get("match_score", 0) < 0.5:
                continue

            if pid not in matches:
                product["source_url"] = source.get("url", "")
                product["source_title"] = source.get("title", "")
                matches[pid] = product

    # Sort: in-stock first, then by match_score
    result = list(matches.values())
    result.sort(
        key=lambda x: (x.get("in_stock", False), x.get("match_score", 0)),
        reverse=True,
    )
    return result[:10]  # Cap at 10


def _extract_thickness_mm(text: str) -> float | None:
    """Extract thickness (mm) from a product name string."""
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*mm", text, re.IGNORECASE)
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", "."))
    except Exception:
        return None


def _is_relevant_result(title: str, snippet: str, product_name: str) -> bool:
    """Check if a search result is relevant for MDF product research."""
    combined = (title + " " + snippet).lower()

    # Must mention MDF or common related terms
    mdf_terms = ["mdf", "melamina", "chapa", "painel", "madeira", "marcenaria"]
    if not any(term in combined for term in mdf_terms):
        return False

    # Must contain at least one word from the product name
    product_words = product_name.lower().split()
    matches = sum(1 for w in product_words if w in combined and len(w) > 2)

    return matches >= 1
