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
