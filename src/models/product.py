from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ProductBase(BaseModel):
    brand: str
    product_name: str
    product_code: str
    thickness_mm: Optional[float] = None
    finish: Optional[str] = None
    width_mm: Optional[float] = None
    height_mm: Optional[float] = None
    color_family: Optional[str] = None
    category: Optional[str] = None
    image_path: Optional[str] = None


class Product(ProductBase):
    id: int
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ProductWithStock(Product):
    quantity_available: float = 0
    quantity_reserved: float = 0
    location: Optional[str] = None

    @property
    def net_available(self) -> float:
        return self.quantity_available - self.quantity_reserved

    @property
    def in_stock(self) -> bool:
        return self.net_available > 0


class ProductSearchResult(ProductWithStock):
    match_score: float = 0.0
    match_type: str = ""  # "exact_code", "exact_name", "fuzzy"
