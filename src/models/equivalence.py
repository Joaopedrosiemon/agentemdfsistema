from pydantic import BaseModel
from typing import Optional
from src.models.product import ProductWithStock


class DirectEquivalence(BaseModel):
    id: int
    product_id_a: int
    product_id_b: int
    equivalence_source: Optional[str] = None
    confidence: float = 1.0
    notes: Optional[str] = None


class EquivalenceResult(BaseModel):
    product: ProductWithStock
    equivalence_source: Optional[str] = None
    confidence: float = 1.0
    notes: Optional[str] = None
