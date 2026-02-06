"""Tests for slot endpoints (client + admin)."""

import pytest
from app.models.models import SlotStatus


async def test_get_available_slots(client, seed_slot):
    r = await client.get("/api/slots/", params={"date": "2026-12-25"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["status"] == "available"


async def test_get_slots_empty_date(client):
    r = await client.get("/api/slots/", params={"date": "2026-01-01"})
    assert r.status_code == 200
    assert r.json() == []


async def test_get_slots_missing_date(client):
    r = await client.get("/api/slots/")
    assert r.status_code == 422


# --- Admin endpoints ---


async def test_get_all_slots_admin(admin_client, seed_slot):
    r = await admin_client.get("/api/slots/all", params={"date": "2026-12-25"})
    assert r.status_code == 200
    assert len(r.json()) == 1


async def test_generate_slots(admin_client):
    r = await admin_client.post(
        "/api/slots/generate",
        json={
            "date": "2026-12-26",
            "start_hour": 9,
            "start_minute": 0,
            "end_hour": 11,
            "end_minute": 0,
            "interval_minutes": 30,
        },
    )
    assert r.status_code == 200
    data = r.json()
    # 9:00-11:00 with 30min interval = 4 slots
    assert len(data) == 4
    assert data[0]["start_time"] == "09:00:00"
    assert data[-1]["end_time"] == "11:00:00"


async def test_generate_slots_duplicate(admin_client, seed_slot):
    """Slots already exist for 2026-12-25 → 400."""
    r = await admin_client.post(
        "/api/slots/generate",
        json={"date": "2026-12-25", "start_hour": 9, "start_minute": 0, "end_hour": 12, "end_minute": 0},
    )
    assert r.status_code == 400


async def test_block_slot(admin_client, seed_slot):
    r = await admin_client.patch(
        f"/api/slots/{seed_slot.id}",
        json={"status": "blocked"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "blocked"


async def test_unblock_slot(admin_client, db, seed_slot):
    seed_slot.status = SlotStatus.blocked
    db.add(seed_slot)
    await db.commit()

    r = await admin_client.patch(
        f"/api/slots/{seed_slot.id}",
        json={"status": "available"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "available"


async def test_cannot_change_booked_slot(admin_client, db, seed_slot):
    seed_slot.status = SlotStatus.booked
    db.add(seed_slot)
    await db.commit()

    r = await admin_client.patch(
        f"/api/slots/{seed_slot.id}",
        json={"status": "available"},
    )
    assert r.status_code == 400


async def test_slot_not_found(admin_client):
    r = await admin_client.patch("/api/slots/9999", json={"status": "blocked"})
    assert r.status_code == 404


async def test_invalid_slot_status(admin_client, seed_slot):
    r = await admin_client.patch(
        f"/api/slots/{seed_slot.id}",
        json={"status": "booked"},
    )
    assert r.status_code == 422
