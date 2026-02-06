"""Tests for services endpoint."""

import pytest
from app.models.models import Service


async def test_get_services_empty(client):
    r = await client.get("/api/services/")
    assert r.status_code == 200
    assert r.json() == []


async def test_get_active_services(client, seed_service):
    r = await client.get("/api/services/")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["name"] == "Автозагар"
    assert data[0]["price"] == 50.0


async def test_inactive_service_hidden(client, db, seed_service):
    seed_service.is_active = False
    db.add(seed_service)
    await db.commit()

    r = await client.get("/api/services/")
    assert r.status_code == 200
    assert r.json() == []


# ── Admin CRUD ──


async def test_get_all_services_includes_inactive(admin_client, db, seed_service):
    seed_service.is_active = False
    db.add(seed_service)
    await db.commit()

    r = await admin_client.get("/api/services/all")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["is_active"] is False


async def test_create_service(admin_client):
    r = await admin_client.post(
        "/api/services/",
        json={"name": "Солярий", "price": 25.0, "duration_minutes": 15},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Солярий"
    assert data["price"] == 25.0
    assert data["duration_minutes"] == 15
    assert data["is_active"] is True


async def test_create_service_non_admin(client):
    r = await client.post("/api/services/", json={"name": "Hack", "price": 1.0})
    assert r.status_code == 403


async def test_create_service_validation(admin_client):
    r = await admin_client.post("/api/services/", json={"name": "", "price": 1.0})
    assert r.status_code == 422

    r = await admin_client.post("/api/services/", json={"name": "X", "price": 0})
    assert r.status_code == 422


async def test_update_service(admin_client, seed_service):
    r = await admin_client.patch(
        f"/api/services/{seed_service.id}",
        json={"price": 75.0, "short_description": "Обновлённый"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["price"] == 75.0
    assert data["short_description"] == "Обновлённый"
    assert data["name"] == "Автозагар"  # unchanged


async def test_update_service_not_found(admin_client):
    r = await admin_client.patch("/api/services/999", json={"name": "X"})
    assert r.status_code == 404


async def test_delete_service_soft(admin_client, seed_service):
    r = await admin_client.delete(f"/api/services/{seed_service.id}")
    assert r.status_code == 204

    # Still visible in /all
    r = await admin_client.get("/api/services/all")
    data = r.json()
    assert len(data) == 1
    assert data[0]["is_active"] is False

    # Hidden from public
    r = await admin_client.get("/api/services/")
    assert r.json() == []


async def test_delete_service_not_found(admin_client):
    r = await admin_client.delete("/api/services/999")
    assert r.status_code == 404
