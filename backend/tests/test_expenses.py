"""Tests for admin expense endpoints."""

import pytest


async def test_create_expense(admin_client):
    r = await admin_client.post(
        "/api/expenses/",
        json={"name": "Крем", "amount": 25.50, "month": "2026-02"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Крем"
    assert data["amount"] == 25.50
    assert data["month"] == "2026-02"


async def test_get_expenses(admin_client):
    # Create one
    await admin_client.post(
        "/api/expenses/",
        json={"name": "Крем", "amount": 25.50, "month": "2026-02"},
    )
    r = await admin_client.get("/api/expenses/", params={"month": "2026-02"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["name"] == "Крем"


async def test_get_expenses_wrong_month(admin_client):
    await admin_client.post(
        "/api/expenses/",
        json={"name": "Крем", "amount": 25.50, "month": "2026-02"},
    )
    r = await admin_client.get("/api/expenses/", params={"month": "2026-03"})
    assert r.status_code == 200
    assert r.json() == []


async def test_delete_expense(admin_client):
    create_r = await admin_client.post(
        "/api/expenses/",
        json={"name": "Крем", "amount": 10.0, "month": "2026-02"},
    )
    expense_id = create_r.json()["id"]

    r = await admin_client.delete(f"/api/expenses/{expense_id}")
    assert r.status_code == 200
    assert r.json()["ok"] is True

    # Verify deleted
    r = await admin_client.get("/api/expenses/", params={"month": "2026-02"})
    assert r.json() == []


async def test_delete_nonexistent(admin_client):
    r = await admin_client.delete("/api/expenses/9999")
    assert r.status_code == 404


async def test_invalid_month_format(admin_client):
    r = await admin_client.get("/api/expenses/", params={"month": "2026-13"})
    assert r.status_code == 422


async def test_invalid_expense_amount(admin_client):
    r = await admin_client.post(
        "/api/expenses/",
        json={"name": "Test", "amount": -5.0, "month": "2026-02"},
    )
    assert r.status_code == 422
