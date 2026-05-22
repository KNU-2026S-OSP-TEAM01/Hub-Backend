import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.parking_lot import ParkingLot
from app.schemas.lot import LotOut

router = APIRouter()


@router.get("/lots", response_model=list[LotOut])
async def list_lots(db: AsyncSession = Depends(get_db)) -> list[LotOut]:
    result = await db.execute(select(ParkingLot))
    return result.scalars().all()


@router.get("/lots/{lot_id}", response_model=LotOut)
async def get_lot(lot_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> LotOut:
    result = await db.execute(select(ParkingLot).where(ParkingLot.id == lot_id))
    lot = result.scalar_one_or_none()
    if not lot:
        raise HTTPException(status_code=404, detail="lot_not_found")
    return lot
