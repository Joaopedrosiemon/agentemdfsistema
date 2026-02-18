from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class FeedbackCreate(BaseModel):
    session_id: str
    original_product_id: int
    suggested_product_id: int
    suggestion_type: str  # "direct_equivalence" or "visual_similarity"
    accepted: bool
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = None


class Feedback(FeedbackCreate):
    id: int
    created_at: Optional[datetime] = None


class FeedbackStats(BaseModel):
    total_suggestions: int = 0
    total_accepted: int = 0
    total_rejected: int = 0
    acceptance_rate: float = 0.0
    average_rating: Optional[float] = None
