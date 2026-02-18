"""Feedback persistence service."""

from src.database import queries


def save(
    session_id: str,
    original_product_id: int,
    suggested_product_id: int,
    suggestion_type: str,
    accepted: bool,
    rating: int | None = None,
    comment: str | None = None,
) -> dict:
    """Save feedback and return confirmation."""
    feedback_id = queries.save_feedback(
        session_id=session_id,
        original_product_id=original_product_id,
        suggested_product_id=suggested_product_id,
        suggestion_type=suggestion_type,
        accepted=accepted,
        rating=rating,
        comment=comment,
    )
    return {
        "success": True,
        "feedback_id": feedback_id,
        "message": "Feedback registrado com sucesso!",
    }


def get_stats() -> dict:
    """Get aggregate feedback statistics."""
    return queries.get_feedback_stats()
