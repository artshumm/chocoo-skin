"""Tests for user auth and profile endpoints."""

import pytest


async def test_auth_creates_user(client):
    """First call creates a new user."""
    r = await client.post("/api/users/auth")
    assert r.status_code == 200
    data = r.json()
    assert data["telegram_id"] == 12345
    assert data["username"] == "testuser"
    assert data["role"] == "client"


async def test_auth_returns_existing(client, seed_user):
    """Second call returns the same user."""
    r = await client.post("/api/users/auth")
    assert r.status_code == 200
    data = r.json()
    assert data["telegram_id"] == 12345
    assert data["id"] == seed_user.id


async def test_update_profile(client, seed_user):
    r = await client.patch(
        "/api/users/profile",
        json={
            "first_name": "Новое Имя",
            "phone": "+375291112233",
            "consent_given": True,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["first_name"] == "Новое Имя"
    assert data["phone"] == "+375291112233"
    assert data["consent_given"] is True


async def test_update_profile_invalid_phone(client, seed_user):
    r = await client.patch(
        "/api/users/profile",
        json={"first_name": "Test", "phone": "123", "consent_given": True},
    )
    assert r.status_code == 422


async def test_update_profile_no_consent(client, seed_user):
    r = await client.patch(
        "/api/users/profile",
        json={"first_name": "Test", "phone": "+375291112233", "consent_given": False},
    )
    assert r.status_code == 400


async def test_update_profile_user_not_found(client):
    """No seed_user → 404."""
    r = await client.patch(
        "/api/users/profile",
        json={"first_name": "Test", "phone": "+375291112233", "consent_given": True},
    )
    assert r.status_code == 404
