import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class LotOut(BaseModel):
    id: uuid.UUID
    name: str
    address: str
    total_spaces: int
    available_spaces: int
    base_fee: int
    base_duration_minutes: int
    extra_fee_per_unit: int
    extra_fee_unit_minutes: int
    latitude: float
    longitude: float
    daily_max_fee: Optional[int]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
