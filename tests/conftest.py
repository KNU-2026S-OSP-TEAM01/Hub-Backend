import uuid
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models.parking_lot import ParkingLot


@pytest.fixture
async def db():
    engine = create_async_engine(settings.test_database_url, connect_args={"ssl": False})

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        async with engine.connect() as conn:
            await conn.begin()
            async with async_sessionmaker(bind=conn, expire_on_commit=False)() as session:
                yield session
            await conn.rollback()
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest.fixture
async def client(db):
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def lot(db):
    parking_lot = ParkingLot(
        id=uuid.uuid4(),
        name="테스트 주차장",
        address="경북대학교 북문 앞",
        latitude=35.8895,
        longitude=128.6105,
        total_spaces=100,
        available_spaces=73,
        base_fee=1000,
        base_duration_minutes=30,
        extra_fee_per_unit=200,
        extra_fee_unit_minutes=10,
        daily_max_fee=10000,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(parking_lot)
    await db.flush()
    return parking_lot
