"""Tests for salon info and FAQ endpoints."""

import pytest


async def test_get_salon_default(client):
    """Without seed data, returns default values."""
    r = await client.get("/api/salon")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Chocoo Skin"
    assert data["description"] == "Салон загара"


async def test_get_salon_with_data(client, seed_salon):
    r = await client.get("/api/salon")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Chocoo Skin"
    assert data["address"] == "ул. Тестовая, 1"
    assert data["instagram"] == "@chocoo"


async def test_get_faq_empty(client):
    r = await client.get("/api/faq")
    assert r.status_code == 200
    assert r.json() == []


async def test_get_faq_ordered(client, seed_faq):
    r = await client.get("/api/faq")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 2
    assert items[0]["question"] == "Что это?"
    assert items[1]["question"] == "Цена?"
