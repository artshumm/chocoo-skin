"""Tests for schedule template endpoints."""

import pytest


async def test_get_templates_empty(admin_client):
    r = await admin_client.get("/api/schedule-templates/")
    assert r.status_code == 200
    assert r.json() == []


async def test_upsert_templates(admin_client):
    r = await admin_client.put(
        "/api/schedule-templates/",
        json={
            "templates": [
                {
                    "day_of_week": 0,
                    "start_time": "08:30:00",
                    "end_time": "21:00:00",
                    "interval_minutes": 30,
                    "is_active": True,
                },
                {
                    "day_of_week": 5,
                    "start_time": "09:00:00",
                    "end_time": "16:00:00",
                    "interval_minutes": 30,
                    "is_active": True,
                },
                {
                    "day_of_week": 6,
                    "start_time": "09:00:00",
                    "end_time": "15:00:00",
                    "interval_minutes": 30,
                    "is_active": False,
                },
            ]
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 3
    assert data[0]["day_of_week"] == 0
    assert data[0]["start_time"] == "08:30:00"
    assert data[2]["is_active"] is False


async def test_upsert_replaces_old(admin_client):
    # Create 3 templates
    await admin_client.put(
        "/api/schedule-templates/",
        json={
            "templates": [
                {"day_of_week": 0, "start_time": "08:00:00", "end_time": "20:00:00"},
                {"day_of_week": 1, "start_time": "08:00:00", "end_time": "20:00:00"},
                {"day_of_week": 2, "start_time": "08:00:00", "end_time": "20:00:00"},
            ]
        },
    )

    # Replace with 1 template
    r = await admin_client.put(
        "/api/schedule-templates/",
        json={
            "templates": [
                {"day_of_week": 4, "start_time": "10:00:00", "end_time": "18:00:00"},
            ]
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["day_of_week"] == 4


async def test_duplicate_day_rejected(admin_client):
    r = await admin_client.put(
        "/api/schedule-templates/",
        json={
            "templates": [
                {"day_of_week": 0, "start_time": "08:00:00", "end_time": "20:00:00"},
                {"day_of_week": 0, "start_time": "09:00:00", "end_time": "18:00:00"},
            ]
        },
    )
    assert r.status_code == 400


async def test_invalid_time_range(admin_client):
    r = await admin_client.put(
        "/api/schedule-templates/",
        json={
            "templates": [
                {"day_of_week": 0, "start_time": "20:00:00", "end_time": "08:00:00"},
            ]
        },
    )
    assert r.status_code == 422


async def test_invalid_day_of_week(admin_client):
    r = await admin_client.put(
        "/api/schedule-templates/",
        json={
            "templates": [
                {"day_of_week": 7, "start_time": "08:00:00", "end_time": "20:00:00"},
            ]
        },
    )
    assert r.status_code == 422


async def test_invalid_interval(admin_client):
    r = await admin_client.put(
        "/api/schedule-templates/",
        json={
            "templates": [
                {
                    "day_of_week": 0,
                    "start_time": "08:00:00",
                    "end_time": "20:00:00",
                    "interval_minutes": 5,
                },
            ]
        },
    )
    assert r.status_code == 422
