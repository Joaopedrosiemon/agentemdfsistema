"""Visual similarity service (Option 2) — Claude Vision based."""

import base64
import json
from pathlib import Path
from urllib.parse import urlparse

import anthropic
import requests as http_requests

from src.database import queries
from config.settings import (
    CLAUDE_API_KEY,
    CLAUDE_MODEL,
    IMAGES_DIR,
    MAX_VISUAL_CANDIDATES_PER_BATCH,
    DEFAULT_MIN_STOCK,
)


def find_visual_alternatives(
    product_id: int,
    max_results: int = 5,
    only_in_stock: bool = True,
) -> list[dict]:
    """
    Find visually similar products using Claude Vision.
    First checks cache, then calls Claude Vision for uncached pairs.
    """
    # Check cache first
    cached = queries.get_cached_similarities_for_product(product_id, min_score=0.3)
    if cached:
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

        if results:
            results.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
            return results[:max_results]

    # No cache — call Claude Vision
    original = queries.get_product_by_id(product_id)
    if not original:
        return []

    original_image = _load_image(original["image_path"])
    if not original_image:
        return [{"error": "Imagem do produto original nao encontrada. Opcao 2 requer imagens."}]

    # Get candidates (same category, in stock)
    candidates = _get_candidates(product_id, original.get("category"), only_in_stock)
    if not candidates:
        return []

    # Process in batches
    all_results = []
    for batch in _batch(candidates, MAX_VISUAL_CANDIDATES_PER_BATCH):
        batch_results = _analyze_batch_with_vision(original, original_image, batch)
        all_results.extend(batch_results)

    # Cache results
    for r in all_results:
        queries.save_similarity_cache(
            product_id, r["id"], r["similarity_score"], r.get("justification", "")
        )

    all_results.sort(key=lambda x: x["similarity_score"], reverse=True)
    return all_results[:max_results]


def search_by_uploaded_image(
    image_b64: str,
    image_media_type: str = "image/jpeg",
    max_results: int = 5,
) -> list[dict]:
    """
    Search for similar products by comparing an uploaded image
    against product images in the catalog using Claude Vision.
    """
    if not CLAUDE_API_KEY:
        return [{"error": "Chave da API nao configurada."}]

    # Get all products with images
    all_products = queries.get_all_active_products()
    candidates = []
    for row in all_products:
        product = dict(row)
        if product.get("image_path"):
            img = _load_image(product["image_path"])
            if img:
                product["_image_b64"] = img
                product["_image_media_type"] = _get_image_media_type(product["image_path"])
                # Add stock info
                stock = queries.get_stock_by_product_id(product["id"])
                if stock:
                    product["quantity_available"] = stock["quantity_available"]
                    product["quantity_reserved"] = stock["quantity_reserved"]
                    product["net_available"] = stock["quantity_available"] - stock["quantity_reserved"]
                    product["in_stock"] = product["net_available"] >= DEFAULT_MIN_STOCK
                else:
                    product["quantity_available"] = 0
                    product["quantity_reserved"] = 0
                    product["net_available"] = 0
                    product["in_stock"] = False
                candidates.append(product)

    if not candidates:
        return [{"error": "Nenhum produto com imagem cadastrada para comparar. Cadastre imagens dos produtos primeiro."}]

    # Send to Claude Vision in batches
    all_results = []
    for batch in _batch(candidates, MAX_VISUAL_CANDIDATES_PER_BATCH):
        batch_results = _compare_uploaded_image_with_batch(
            image_b64, image_media_type, batch
        )
        all_results.extend(batch_results)

    all_results.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
    return all_results[:max_results]


def _load_image(image_path: str | None) -> str | None:
    """Load image and return base64 encoded string. Supports local files and URLs."""
    if not image_path:
        return None

    # Check if it's a URL
    if _is_url(image_path):
        return _load_image_from_url(image_path)

    # Local file
    path = Path(image_path)
    if not path.is_absolute():
        path = IMAGES_DIR / path

    if not path.exists():
        return None

    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _is_url(path: str) -> bool:
    """Check if a path is a URL."""
    try:
        result = urlparse(path)
        return result.scheme in ("http", "https")
    except Exception:
        return False


def _load_image_from_url(url: str) -> str | None:
    """Download image from URL and return base64 encoded string."""
    try:
        response = http_requests.get(url, timeout=10)
        response.raise_for_status()
        return base64.b64encode(response.content).decode("utf-8")
    except Exception:
        return None


def _get_image_media_type(image_path: str) -> str:
    """Get media type from file extension or URL."""
    if _is_url(image_path):
        # Try to get extension from URL
        parsed = urlparse(image_path)
        path = parsed.path
    else:
        path = image_path

    ext = Path(path).suffix.lower()
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    return media_types.get(ext, "image/jpeg")


def _get_candidates(
    exclude_product_id: int,
    category: str | None,
    only_in_stock: bool,
) -> list[dict]:
    """Get candidate products for visual comparison."""
    if category:
        rows = queries.get_products_by_category(category)
    else:
        rows = queries.get_all_active_products()

    candidates = []
    for row in rows:
        product = dict(row)
        if product["id"] == exclude_product_id:
            continue
        if not product.get("image_path"):
            continue

        # Check stock
        if only_in_stock:
            stock = queries.get_stock_by_product_id(product["id"])
            if not stock or (stock["quantity_available"] - stock["quantity_reserved"]) < DEFAULT_MIN_STOCK:
                continue
            product["quantity_available"] = stock["quantity_available"]
            product["quantity_reserved"] = stock["quantity_reserved"]
            product["net_available"] = stock["quantity_available"] - stock["quantity_reserved"]
            product["in_stock"] = True
        else:
            product["net_available"] = 0
            product["in_stock"] = False

        candidates.append(product)

    return candidates


def _batch(items: list, size: int):
    """Split list into batches."""
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _analyze_batch_with_vision(
    original: dict, original_image_b64: str, candidates: list[dict]
) -> list[dict]:
    """Send a batch of images to Claude Vision for similarity analysis."""
    if not CLAUDE_API_KEY:
        return []

    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

    # Build content with images
    content = [
        {
            "type": "text",
            "text": (
                f"Voce e um especialista em MDF. Analise a similaridade visual entre o produto original "
                f"e os candidatos abaixo.\n\n"
                f"PRODUTO ORIGINAL: {original['brand']} {original['product_name']} ({original['product_code']})\n"
                f"Imagem do original:"
            ),
        },
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": _get_image_media_type(original.get("image_path", "image.jpg")),
                "data": original_image_b64,
            },
        },
        {"type": "text", "text": "\nCANDIDATOS para comparacao:"},
    ]

    # Add candidate images
    for i, candidate in enumerate(candidates):
        candidate_image = _load_image(candidate.get("image_path"))
        if not candidate_image:
            continue

        content.append({
            "type": "text",
            "text": f"\nCandidato {i + 1}: {candidate['brand']} {candidate['product_name']} ({candidate['product_code']})",
        })
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": _get_image_media_type(candidate.get("image_path", "image.jpg")),
                "data": candidate_image,
            },
        })

    content.append({
        "type": "text",
        "text": (
            "\nPara CADA candidato, retorne um JSON array com objetos contendo:\n"
            '- "product_code": codigo do candidato\n'
            '- "similarity_score": float de 0.0 a 1.0 (quanto mais parecido, maior)\n'
            '- "justification": breve justificativa em portugues (tom, textura, veio, cor)\n\n'
            "Responda APENAS com o JSON array, sem texto adicional."
        ),
    })

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": content}],
        )

        response_text = response.content[0].text.strip()
        # Extract JSON from response
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        scores = json.loads(response_text)

        # Merge scores with candidate data
        results = []
        candidate_map = {c["product_code"]: c for c in candidates}
        for score_entry in scores:
            code = score_entry.get("product_code", "")
            if code in candidate_map:
                result = candidate_map[code].copy()
                result["similarity_score"] = score_entry.get("similarity_score", 0)
                result["justification"] = score_entry.get("justification", "")
                results.append(result)

        return results

    except Exception:
        return []


def _compare_uploaded_image_with_batch(
    uploaded_image_b64: str,
    uploaded_media_type: str,
    candidates: list[dict],
) -> list[dict]:
    """Compare an uploaded image against a batch of product images."""
    if not CLAUDE_API_KEY:
        return []

    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

    content = [
        {
            "type": "text",
            "text": (
                "Voce e um especialista em MDF. O vendedor enviou uma foto de um MDF. "
                "Compare com os produtos cadastrados abaixo e identifique os mais parecidos.\n\n"
                "FOTO DO VENDEDOR:"
            ),
        },
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": uploaded_media_type,
                "data": uploaded_image_b64,
            },
        },
        {"type": "text", "text": "\nPRODUTOS CADASTRADOS para comparacao:"},
    ]

    # Add candidate images
    for i, candidate in enumerate(candidates):
        img_b64 = candidate.get("_image_b64")
        if not img_b64:
            img_b64 = _load_image(candidate.get("image_path"))
        if not img_b64:
            continue

        content.append({
            "type": "text",
            "text": f"\nProduto {i + 1}: {candidate['brand']} {candidate['product_name']} ({candidate['product_code']})",
        })
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": candidate.get("_image_media_type", "image/jpeg"),
                "data": img_b64,
            },
        })

    content.append({
        "type": "text",
        "text": (
            "\nPara CADA produto cadastrado, retorne um JSON array com objetos contendo:\n"
            '- "product_code": codigo do produto\n'
            '- "similarity_score": float de 0.0 a 1.0 (quanto mais parecido com a foto do vendedor, maior)\n'
            '- "justification": breve justificativa em portugues (tom, textura, veio, cor, conceito estetico)\n\n'
            "Responda APENAS com o JSON array, sem texto adicional."
        ),
    })

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": content}],
        )

        response_text = response.content[0].text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        scores = json.loads(response_text)

        results = []
        candidate_map = {c["product_code"]: c for c in candidates}
        for score_entry in scores:
            code = score_entry.get("product_code", "")
            if code in candidate_map:
                result = candidate_map[code].copy()
                # Remove internal image data from result
                result.pop("_image_b64", None)
                result.pop("_image_media_type", None)
                result["similarity_score"] = score_entry.get("similarity_score", 0)
                result["justification"] = score_entry.get("justification", "")
                results.append(result)

        return results

    except Exception:
        return []
