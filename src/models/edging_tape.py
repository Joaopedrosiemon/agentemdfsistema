from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class EdgingTapeBase(BaseModel):
    brand: str
    tape_name: str
    tape_code: str
    width_mm: Optional[float] = None
    thickness_mm: Optional[float] = None
    finish: Optional[str] = None
    color_family: Optional[str] = None


class EdgingTape(EdgingTapeBase):
    id: int
    is_active: bool = True
    created_at: Optional[datetime] = None


class TapeCompatibility(BaseModel):
    tape: EdgingTape
    compatibility_type: str = "official"  # "official", "recommended", "alternative"


class TapeSearchResult(BaseModel):
    compatible_tapes: list[TapeCompatibility] = []
    product_code: str = ""
    product_name: str = ""
