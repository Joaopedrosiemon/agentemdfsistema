"""Smart alternatives service (improved Option 2) — attribute + knowledge based."""

import json

import anthropic

from src.database import queries
from config.settings import (
    CLAUDE_API_KEY,
    CLAUDE_MODEL,
    DEFAULT_MIN_STOCK,
)

# ── Wood Family Mapping ──────────────────────────────────────
# Keywords found in product names → semantic wood/pattern family

WOOD_FAMILIES = {
    # Carvalho (oak) family
    "carvalho": "carvalho",
    "oak": "carvalho",
    "rovere": "carvalho",
    "hanover": "carvalho",
    # Nogal (walnut) family
    "nogal": "nogal",
    "nogueira": "nogal",
    "walnut": "nogal",
    # Cedar family
    "cedro": "cedro",
    "cedrinho": "cedro",
    "cedar": "cedro",
    # Freijo / Louro family
    "freijo": "freijo",
    "louro": "freijo",
    "cumaru": "freijo",
    # Tropical woods
    "ipanema": "tropical",
    "itapua": "tropical",
    "jatoba": "tropical",
    "jequitiba": "tropical",
    "canela": "tropical",
    "castanho": "tropical",
    "castanheira": "tropical",
    "acacia": "tropical",
    "savana": "tropical",
    "lenho": "tropical",
    # Almond / warm tones
    "amendoa": "amendoa",
    "amendoeira": "amendoa",
    "ameixa": "amendoa",
    "avela": "amendoa",
    "damasco": "amendoa",
    "gengibre": "amendoa",
    "pecan": "amendoa",
    # Others
    "imbuia": "imbuia",
    "teca": "teca",
    "teka": "teca",
    "montana": "montana",
    "melbourne": "montana",
    "pinho": "pinho",
    "maple": "maple",
    "rustico": "rustico",
}

# ── Color Family Mapping ─────────────────────────────────────

COLOR_FAMILIES = {
    # White
    "branco": "branco",
    "neve": "branco",
    "white": "branco",
    "artico": "branco",
    # Gray
    "cinza": "cinza",
    "grafite": "cinza",
    "grafito": "cinza",
    "titanio": "cinza",
    "chumbo": "cinza",
    # Black
    "preto": "preto",
    "black": "preto",
    # Neutral / light tones
    "areia": "neutro_claro",
    "beige": "neutro_claro",
    "creme": "neutro_claro",
    "marfim": "neutro_claro",
    "perola": "neutro_claro",
    # Green
    "verde": "verde",
    "erva": "verde",
    "salvia": "verde",
    "selva": "verde",
    # Blue
    "azul": "azul",
    "petroleo": "azul",
    # Brown / earth tones (for unicolor)
    "chocolate": "marrom",
    "cafe": "marrom",
    "tabaco": "marrom",
}

# ── Finish compatibility groups ──────────────────────────────

FINISH_GROUPS = [
    {"design", "essencial", "nature", "natura"},
    {"matt", "soft", "supermatte", "acetinatta"},
    {"chess", "trama", "pele"},
    {"lacca", "liso"},
    {"silk", "linho"},
]


def find_smart_alternatives(
    product_id: int,
    max_results: int = 3,
    only_in_stock: bool = True,
) -> list[dict]:
    """
    Find alternative products using attribute matching + Claude knowledge.
    Phase 1: Attribute pre-filter (instant, zero cost)
    Phase 2: Claude ranking (one text-only API call)
    Results are cached in similarity_cache.
    """
    # Check cache first
    cached = queries.get_cached_similarities_for_product(product_id, min_score=0.3)
    if cached:
        results = _filter_and_format_cached(cached, only_in_stock)
        if results:
            return results[:max_results]

    # Load original product
    original = queries.get_product_by_id(product_id)
    if not original:
        return [{"error": "Produto nao encontrado."}]

    original = dict(original)

    # Phase 1: Attribute pre-filter
    candidates = _attribute_prefilter(original, only_in_stock, limit=20)
    if not candidates:
        return [{"error": f"Nenhum produto similar encontrado em estoque na categoria '{original.get('category', 'N/A')}'."}]

    # Phase 2: Claude knowledge ranking
    ranked = _claude_rank_alternatives(original, candidates)

    if not ranked:
        # Fallback: return attribute-only results if Claude fails
        for c in candidates:
            c["similarity_score"] = c.get("attribute_score", 0.5)
            c["justification"] = f"Similar por categoria ({c.get('category')}) e atributos."
        ranked = candidates

    # Cache all results
    for r in ranked:
        queries.save_similarity_cache(
            product_id, r["id"], r["similarity_score"], r.get("justification", "")
        )

    ranked.sort(key=lambda x: x["similarity_score"], reverse=True)
    return ranked[:max_results]


def _attribute_prefilter(
    original: dict, only_in_stock: bool, limit: int = 20
) -> list[dict]:
    """Phase 1: Score all in-stock products by attribute similarity."""
    original_attrs = _extract_attributes(original)

    # Get all products with stock
    if only_in_stock:
        all_products = queries.get_products_in_stock(DEFAULT_MIN_STOCK)
    else:
        all_products = queries.get_all_active_products()

    scored = []
    for row in all_products:
        product = dict(row)
        if product["id"] == original["id"]:
            continue

        candidate_attrs = _extract_attributes(product)
        score = _compute_attribute_score(original_attrs, candidate_attrs)

        if score > 0.15:  # minimum relevance threshold
            product["attribute_score"] = round(score, 3)
            # Add stock info if not already present
            if "quantity_available" not in product:
                stock = queries.get_stock_by_product_id(product["id"])
                if stock:
                    product["quantity_available"] = stock["quantity_available"]
                    product["quantity_reserved"] = stock["quantity_reserved"]
                    product["net_available"] = (
                        stock["quantity_available"] - stock["quantity_reserved"]
                    )
                else:
                    product["net_available"] = 0
            else:
                qty_avail = product.get("quantity_available") or 0
                qty_res = product.get("quantity_reserved") or 0
                product["net_available"] = qty_avail - qty_res

            scored.append(product)

    scored.sort(key=lambda x: x["attribute_score"], reverse=True)
    return scored[:limit]


def _extract_attributes(product: dict) -> dict:
    """Extract semantic attributes from a product."""
    name = (product.get("product_name") or "").upper()
    name_lower = name.lower()

    attrs = {
        "category": product.get("category", "outro"),
        "finish": (product.get("finish") or "").lower(),
        "thickness": product.get("thickness_mm"),
        "wood_family": None,
        "color_family": None,
        "brand": (product.get("brand") or ""),
    }

    # Extract wood family
    for keyword, family in WOOD_FAMILIES.items():
        if keyword in name_lower:
            attrs["wood_family"] = family
            break

    # Extract color family
    for keyword, family in COLOR_FAMILIES.items():
        if keyword in name_lower:
            attrs["color_family"] = family
            break

    return attrs


def _compute_attribute_score(original: dict, candidate: dict) -> float:
    """Compute similarity score based on attribute overlap."""
    score = 0.0

    # Same category is essential (madeirado vs unicolor should not match)
    if original["category"] == candidate["category"]:
        score += 0.30
    elif original["category"] == "outro" or candidate["category"] == "outro":
        score += 0.10  # "outro" is fuzzy, partial credit
    else:
        return 0.0  # Different main categories -> not similar

    # Wood family match (for madeirado)
    if original.get("wood_family") and candidate.get("wood_family"):
        if original["wood_family"] == candidate["wood_family"]:
            score += 0.30
        else:
            score += 0.05  # Different wood but same category

    # Color family match (for unicolor/fantasia)
    if original.get("color_family") and candidate.get("color_family"):
        if original["color_family"] == candidate["color_family"]:
            score += 0.30

    # Finish match
    if original["finish"] and candidate["finish"]:
        if original["finish"] == candidate["finish"]:
            score += 0.10
        elif _finishes_compatible(original["finish"], candidate["finish"]):
            score += 0.05

    # Thickness match
    if original["thickness"] and candidate["thickness"]:
        if original["thickness"] == candidate["thickness"]:
            score += 0.10

    return min(score, 1.0)


def _finishes_compatible(finish_a: str, finish_b: str) -> bool:
    """Check if two finishes are in the same family."""
    a_lower = finish_a.lower()
    b_lower = finish_b.lower()
    for group in FINISH_GROUPS:
        a_in = any(kw in a_lower for kw in group)
        b_in = any(kw in b_lower for kw in group)
        if a_in and b_in:
            return True
    return False


def _claude_rank_alternatives(
    original: dict, candidates: list[dict]
) -> list[dict]:
    """Phase 2: Use Claude's knowledge to rank and justify alternatives."""
    if not CLAUDE_API_KEY:
        return []

    # Build compact candidate list for the prompt
    candidate_descriptions = []
    for i, c in enumerate(candidates):
        desc = (
            f"{i+1}. {c.get('brand', '?')} {c.get('product_name', '?')} "
            f"(espessura: {c.get('thickness_mm', '?')}mm, "
            f"acabamento: {c.get('finish', 'N/A')}, "
            f"categoria: {c.get('category', 'N/A')}, "
            f"estoque: {c.get('net_available', 0)} chapas)"
        )
        candidate_descriptions.append(desc)

    prompt = (
        "Voce e um especialista em MDF brasileiro. O vendedor precisa de um substituto para:\n\n"
        f"PRODUTO ORIGINAL: {original.get('brand', '?')} {original.get('product_name', '?')}\n"
        f"- Espessura: {original.get('thickness_mm', 'N/A')}mm\n"
        f"- Acabamento: {original.get('finish', 'N/A')}\n"
        f"- Categoria: {original.get('category', 'N/A')}\n\n"
        "NAO existe equivalencia direta na tabela. Analise os candidatos abaixo e "
        "classifique pela SIMILARIDADE VISUAL/ESTETICA com o produto original. "
        "Considere: tom de cor, padrao do veio (se madeirado), textura, conceito estetico geral.\n\n"
        "CANDIDATOS EM ESTOQUE:\n"
        f"{chr(10).join(candidate_descriptions)}\n\n"
        "Retorne APENAS um JSON array (sem markdown, sem ```). Formato EXATO:\n"
        '[{"index": 1, "similarity_score": 0.85, "justification": "texto curto"}, ...]\n\n'
        "REGRAS:\n"
        '- "index": numero do candidato (1, 2, 3...)\n'
        '- "similarity_score": float de 0.0 a 1.0\n'
        '- "justification": frase curta em portugues\n'
        "- Use EXATAMENTE esses nomes de campo em ingles\n"
        "- Responda APENAS o JSON array, nada mais"
    )

    try:
        client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = response.content[0].text.strip()
        # Extract JSON from response (handle markdown code blocks)
        if "```" in response_text:
            parts = response_text.split("```")
            for part in parts:
                cleaned = part.strip()
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:].strip()
                if cleaned.startswith("["):
                    response_text = cleaned
                    break
        scores = json.loads(response_text)

        # Merge scores with candidate data (handle field name variations)
        results = []
        for score_entry in scores:
            # Accept "index", "candidato", or numbered position
            idx = (
                score_entry.get("index")
                or score_entry.get("candidato")
                or 0
            ) - 1

            # Accept score field variations
            sim_score = (
                score_entry.get("similarity_score")
                or score_entry.get("similaridade_visual")
                or score_entry.get("score")
                or 0
            )
            # Normalize if score is 0-100 instead of 0.0-1.0
            if isinstance(sim_score, (int, float)) and sim_score > 1.0:
                sim_score = sim_score / 100.0

            # Accept justification field variations
            justification = (
                score_entry.get("justification")
                or score_entry.get("justificativa")
                or score_entry.get("reason")
                or ""
            )

            if 0 <= idx < len(candidates):
                result = candidates[idx].copy()
                result["similarity_score"] = round(sim_score, 2)
                result["justification"] = justification
                result.pop("attribute_score", None)
                results.append(result)

        return results

    except Exception:
        return []


def _filter_and_format_cached(cached: list, only_in_stock: bool) -> list[dict]:
    """Filter and format cached similarity results."""
    results = []
    for row in cached:
        product = dict(row)
        qty_available = product.get("quantity_available") or 0
        qty_reserved = product.get("quantity_reserved") or 0
        net = qty_available - qty_reserved

        if only_in_stock and net < DEFAULT_MIN_STOCK:
            continue

        product["net_available"] = net
        product["in_stock"] = net >= DEFAULT_MIN_STOCK
        results.append(product)

    results.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
    return results
