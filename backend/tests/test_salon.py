"""Tests for salon info and FAQ endpoints."""

import pytest


async def test_get_salon_default(client):
    """Without seed data, returns default values."""
    r = await client.get("/api/salon")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Салон"
    assert data["description"] == ""


async def test_get_salon_with_data(client, seed_salon):
    r = await client.get("/api/salon")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Test Salon"
    assert data["address"] == "ул. Тестовая, 1"
    assert data["instagram"] == "@testsalon"


async def test_update_salon_creates_if_missing(admin_client):
    """PATCH creates salon record if none exists."""
    r = await admin_client.patch("/api/salon", json={"name": "New Name", "address": "ул. Новая, 5"})
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "New Name"
    assert data["address"] == "ул. Новая, 5"
    assert data["phone"] == ""  # default


async def test_update_salon_partial(admin_client, seed_salon):
    """PATCH updates only provided fields."""
    r = await admin_client.patch("/api/salon", json={"phone": "+375291111111"})
    assert r.status_code == 200
    data = r.json()
    assert data["phone"] == "+375291111111"
    assert data["name"] == "Test Salon"  # unchanged
    assert data["address"] == "ул. Тестовая, 1"  # unchanged


async def test_update_salon_non_admin(client):
    """Regular user cannot update salon."""
    r = await client.patch("/api/salon", json={"name": "Hacked"})
    assert r.status_code == 403


async def test_update_salon_validation(admin_client):
    """Empty name rejected."""
    r = await admin_client.patch("/api/salon", json={"name": ""})
    assert r.status_code == 422


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


# ── FAQ CRUD ──


async def test_create_faq(admin_client):
    r = await admin_client.post(
        "/api/faq",
        json={"question": "Как записаться?", "answer": "Через бот", "order_index": 0},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["question"] == "Как записаться?"
    assert data["answer"] == "Через бот"
    assert data["order_index"] == 0


async def test_create_faq_non_admin(client):
    r = await client.post("/api/faq", json={"question": "?", "answer": "!"})
    assert r.status_code == 403


async def test_create_faq_validation(admin_client):
    r = await admin_client.post("/api/faq", json={"question": "", "answer": "X"})
    assert r.status_code == 422


async def test_update_faq(admin_client, seed_faq):
    faq_id = seed_faq[0].id
    r = await admin_client.patch(f"/api/faq/{faq_id}", json={"answer": "Обновлённый ответ"})
    assert r.status_code == 200
    assert r.json()["answer"] == "Обновлённый ответ"
    assert r.json()["question"] == "Что это?"  # unchanged


async def test_update_faq_not_found(admin_client):
    r = await admin_client.patch("/api/faq/999", json={"answer": "X"})
    assert r.status_code == 404


async def test_delete_faq(admin_client, seed_faq):
    faq_id = seed_faq[0].id
    r = await admin_client.delete(f"/api/faq/{faq_id}")
    assert r.status_code == 204

    # Verify deleted
    r = await admin_client.get("/api/faq")
    assert len(r.json()) == 1


async def test_delete_faq_not_found(admin_client):
    r = await admin_client.delete("/api/faq/999")
    assert r.status_code == 404


async def test_reorder_faq(admin_client, seed_faq):
    """Reverse FAQ order."""
    ids = [seed_faq[1].id, seed_faq[0].id]  # reverse
    r = await admin_client.put("/api/faq/reorder", json={"ids": ids})
    assert r.status_code == 200
    data = r.json()
    assert data[0]["question"] == "Цена?"
    assert data[1]["question"] == "Что это?"


async def test_reorder_faq_invalid_ids(admin_client, seed_faq):
    r = await admin_client.put("/api/faq/reorder", json={"ids": [999, 998]})
    assert r.status_code == 400
