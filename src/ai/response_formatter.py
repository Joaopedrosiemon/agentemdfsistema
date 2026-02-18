"""Format structured data into text for client messages."""

from src.database import queries


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
    else:
        header = "SUGESTAO - ALTERNATIVA VISUAL"
        explanation = (
            "Este produto mantem o mesmo conceito estetico do solicitado, "
            "com visual muito semelhante."
        )

    # Get edging tape
    tapes = queries.get_compatible_tapes(suggested_product_id)
    tape_text = ""
    if tapes:
        tape = tapes[0]
        tape_text = f"\nFita de borda compativel: {tape['brand']} {tape['tape_name']} ({tape['tape_code']})"

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
