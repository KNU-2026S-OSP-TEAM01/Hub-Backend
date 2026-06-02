import uuid
from datetime import datetime

from sqlalchemy import DateTime, Double, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ParkingLot(Base):
    __tablename__ = "parking_lots"

    id:                     Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), primary_key=True)
    name:                   Mapped[str]        = mapped_column(String(100), nullable=False)
    address:                Mapped[str]        = mapped_column(String(255), nullable=False)
    latitude:               Mapped[float]      = mapped_column(Double, nullable=False)
    longitude:              Mapped[float]      = mapped_column(Double, nullable=False)
    total_spaces:           Mapped[int]        = mapped_column(Integer, nullable=False)
    available_spaces:       Mapped[int]        = mapped_column(Integer, nullable=False)
    base_fee:               Mapped[int]        = mapped_column(Integer, nullable=False)
    base_duration_minutes:  Mapped[int]        = mapped_column(Integer, nullable=False)
    extra_fee_per_unit:     Mapped[int]        = mapped_column(Integer, nullable=False)
    extra_fee_unit_minutes: Mapped[int]        = mapped_column(Integer, nullable=False)
    daily_max_fee:          Mapped[int | None] = mapped_column(Integer)
    created_at:             Mapped[datetime]   = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at:             Mapped[datetime]   = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
