import uuid

from httpx import AsyncClient


# ── GET /api/v1/lots ──────────────────────────────────────────────────────────

async def test_list_lots_returns_lot(client: AsyncClient, lot):
    res = await client.get("/api/v1/lots")
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 1
    assert body[0]["name"] == "테스트 주차장"


async def test_list_lots_excludes_sensitive_fields(client: AsyncClient, lot):
    res = await client.get("/api/v1/lots")
    item = res.json()[0]
    assert "owner_user_id" not in item
    assert "api_key" not in item


async def test_list_lots_returns_empty_when_no_lots(client: AsyncClient):
    res = await client.get("/api/v1/lots")
    assert res.status_code == 200
    assert res.json() == []


async def test_list_lots_returns_correct_fields(client: AsyncClient, lot):
    res = await client.get("/api/v1/lots")
    item = res.json()[0]
    assert item["id"] == str(lot.id)
    assert item["available_spaces"] == 73
    assert item["base_fee"] == 1000
    assert item["daily_max_fee"] == 10000


# ── GET /api/v1/lots/{lot_id} ─────────────────────────────────────────────────

async def test_get_lot_returns_lot(client: AsyncClient, lot):
    res = await client.get(f"/api/v1/lots/{lot.id}")
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == str(lot.id)
    assert body["name"] == "테스트 주차장"
    assert body["address"] == "경북대학교 북문 앞"


async def test_get_lot_excludes_sensitive_fields(client: AsyncClient, lot):
    res = await client.get(f"/api/v1/lots/{lot.id}")
    body = res.json()
    assert "owner_user_id" not in body
    assert "api_key" not in body


async def test_get_lot_not_found(client: AsyncClient):
    res = await client.get(f"/api/v1/lots/{uuid.uuid4()}")
    assert res.status_code == 404
    assert res.json()["detail"] == "lot_not_found"


async def test_get_lot_daily_max_fee_none(client: AsyncClient, db):
    from app.models.parking_lot import ParkingLot
    from datetime import datetime, timezone
    no_max = ParkingLot(
        id=uuid.uuid4(),
        name="무제한 주차장",
        total_spaces=50,
        available_spaces=50,
        base_fee=0,
        base_duration_minutes=0,
        extra_fee_per_unit=0,
        extra_fee_unit_minutes=10,
        daily_max_fee=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(no_max)
    await db.flush()

    res = await client.get(f"/api/v1/lots/{no_max.id}")
    assert res.status_code == 200
    assert res.json()["daily_max_fee"] is None
