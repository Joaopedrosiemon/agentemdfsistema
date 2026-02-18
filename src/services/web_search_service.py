"""Web search service for MDF product research via Brave Search API."""

import requests as http_requests

from config.settings import BRAVE_API_KEY

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"


def is_web_search_available() -> bool:
    """Check if web search is configured and available."""
    return bool(BRAVE_API_KEY)


def search_mdf_references(product_name: str, brand: str = "") -> list[dict]:
    """
    Search the web for MDF product references and alternatives.

    Returns list of relevant search results with title, snippet, and URL.
    """
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

        for item in web_results[:5]:
            title = item.get("title", "")
            snippet = item.get("description", "")
            url = item.get("url", "")

            # Filter out irrelevant results
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


def _is_relevant_result(title: str, snippet: str, product_name: str) -> bool:
    """Check if a search result is relevant for MDF product research."""
    combined = (title + " " + snippet).lower()

    # Must mention MDF or common related terms
    mdf_terms = ["mdf", "melamina", "chapa", "painel", "madeira", "marcenaria"]
    if not any(term in combined for term in mdf_terms):
        return False

    # Bonus: contains product-related keywords
    product_words = product_name.lower().split()
    matches = sum(1 for w in product_words if w in combined and len(w) > 2)

    return matches >= 1
