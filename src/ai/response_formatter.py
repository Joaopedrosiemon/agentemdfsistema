"""Format structured data into text for client messages."""

from src.database import queries
from src.services import edging_tape_service


def generate_client_text(
    original_product_id: int,
    suggested_product_id: int,
    suggestion_type: str,
) -> dict:
    """Generate copy-to-clipboard text for the client."""
    original = queries.get_product_by_id(original_product_id)
    substitute = queries.get_product_by_id(suggested_product_id)

    if not original or not substitute:
        return {"success": False, "error": "Produto nao encontrado"}

    if suggestion_type == "direct_equivalence":
        header = "SUBSTITUICAO - EQUIVALENCIA DIRETA"
        explanation = "Este produto e equivalente oficial ao solicitado, apenas de marca diferente."
    elif suggestion_type == "web_suggestion":
        header = "SUGESTAO - REFERENCIA DE MERCADO"
        explanation = (
            "Este produto foi identificado como alternativa com base em "
            "referencias de mercado e esta disponivel em nosso estoque."
        )
    else:
        header = "SUGESTAO - ALTERNATIVA VISUAL"
        explanation = (
            "Este produto mantem o mesmo conceito estetico do solicitado, "
            "com visual muito semelhante."
        )

    # Get edging tape
    tapes = edging_tape_service.find_tape_for_substitute(
        original_product_id, suggested_product_id
    )
    tape_text = ""
    if tapes:
        tape = tapes[0]
        tape_text = (
            f"\nFita de borda compativel: {tape['brand']} {tape['tape_name']} "
            f"({tape['tape_code']})"
        )
        if "quantity_available" in tape:
            tape_text += f"\nEstoque fita: {_format_rolls(tape.get('quantity_available', 0))} rolos"

    text = (
        f"{header}\n"
        f"\n"
        f"Produto solicitado: {original['brand']} {original['product_name']} ({original['product_code']})\n"
        f"Status: Indisponivel no momento\n"
        f"\n"
        f"Alternativa sugerida: {substitute['brand']} {substitute['product_name']} ({substitute['product_code']})\n"
    )

    if substitute.get("thickness_mm"):
        text += f"Espessura: {substitute['thickness_mm']}mm\n"
    if substitute.get("finish"):
        text += f"Acabamento: {substitute['finish']}\n"

    text += f"\n{explanation}"
    text += tape_text

    return {
        "success": True,
        "text": text.strip(),
    }


def _format_rolls(value: float) -> str:
    try:
        v = float(value)
    except Exception:
        return "0"
    if v.is_integer():
        return str(int(v))
    return f"{v:.2f}".rstrip("0").rstrip(".")
