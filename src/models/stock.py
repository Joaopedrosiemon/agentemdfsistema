from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class StockBase(BaseModel):
    product_code: str
    quantity_available: float = 0
    quantity_reserved: float = 0
    minimum_stock: float = 0
    location: str = "principal"
    unit: str = "chapa"


class Stock(BaseModel):
    id: int
    product_id: int
    quantity_available: float = 0
    quantity_reserved: float = 0
    minimum_stock: float = 0
    location: str = "principal"
    unit: str = "chapa"
    last_updated: Optional[datetime] = None

    @property
    def net_available(self) -> float:
        return self.quantity_available - self.quantity_reserved

    @property
    def is_low(self) -> bool:
        return self.net_available <= self.minimum_stock

    @property
    def in_stock(self) -> bool:
        return self.net_available > 0
