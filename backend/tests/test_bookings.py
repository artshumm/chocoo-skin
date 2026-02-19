"""Tests for booking flow: create, list, cancel."""

import pytest
from app.models.models import Booking, BookingStatus, SlotStatus


async def test_create_booking(client, seed_user, seed_service, seed_slot, mock_notifications):
    r = await client.post(
        "/api/bookings/",
        json={
            "service_id": seed_service.id,
            "slot_id": seed_slot.id,
            "remind_before_hours": 2,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "confirmed"
    assert data["service"]["name"] == "Автозагар"
    assert data["slot"]["date"] == "2026-12-25"
    assert data["client"]["telegram_id"] == 12345
    # Notifications were called
    mock_notifications["new"].assert_called_once()
    mock_notifications["confirmed"].assert_called_once()


async def test_create_booking_no_user(client, seed_service, seed_slot, mock_notifications):
    """User not registered → 404."""
    r = await client.post(
        "/api/bookings/",
        json={"service_id": seed_service.id, "slot_id": seed_slot.id},
    )
    assert r.status_code == 404


async def test_create_booking_no_consent(client, db, seed_service, seed_slot, mock_notifications):
    """User without consent+phone → 400."""
    from app.models.models import User

    user = User(telegram_id=12345, username="testuser", first_name="Test", consent_given=False)
    db.add(user)
    await db.commit()

    r = await client.post(
        "/api/bookings/",
        json={"service_id": seed_service.id, "slot_id": seed_slot.id},
    )
    assert r.status_code == 400


async def test_create_booking_slot_taken(client, db, seed_user, seed_service, seed_slot, mock_notifications):
    """Booked slot → 400."""
    seed_slot.status = SlotStatus.booked
    db.add(seed_slot)
    await db.commit()

    r = await client.post(
        "/api/bookings/",
        json={"service_id": seed_service.id, "slot_id": seed_slot.id},
    )
    assert r.status_code == 400


async def test_create_booking_invalid_service(client, seed_user, seed_slot, mock_notifications):
    r = await client.post(
        "/api/bookings/",
        json={"service_id": 9999, "slot_id": seed_slot.id},
    )
    assert r.status_code == 404


async def test_get_my_bookings_empty(client):
    r = await client.get("/api/bookings/my")
    assert r.status_code == 200
    assert r.json() == []


async def test_get_my_bookings(client, seed_user, seed_service, seed_slot, mock_notifications):
    # Create a booking first
    await client.post(
        "/api/bookings/",
        json={"service_id": seed_service.id, "slot_id": seed_slot.id},
    )
    r = await client.get("/api/bookings/my")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["status"] == "confirmed"


async def test_cancel_booking(client, seed_user, seed_service, seed_slot, mock_notifications):
    # Create booking
    create_r = await client.post(
        "/api/bookings/",
        json={"service_id": seed_service.id, "slot_id": seed_slot.id},
    )
    booking_id = create_r.json()["id"]

    # Cancel it
    r = await client.patch(f"/api/bookings/{booking_id}/cancel")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "cancelled"
    assert data["slot"]["status"] == "available"
    mock_notifications["cancelled"].assert_called_once()


async def test_cancel_already_cancelled(client, seed_user, seed_service, seed_slot, mock_notifications):
    create_r = await client.post(
        "/api/bookings/",
        json={"service_id": seed_service.id, "slot_id": seed_slot.id},
    )
    booking_id = create_r.json()["id"]
    await client.patch(f"/api/bookings/{booking_id}/cancel")

    # Try cancelling again
    r = await client.patch(f"/api/bookings/{booking_id}/cancel")
    assert r.status_code == 400


async def test_cancel_nonexistent(client):
    r = await client.patch("/api/bookings/9999/cancel")
    assert r.status_code == 404


# --- Admin endpoints ---


async def test_get_all_bookings_admin(admin_client):
    r = await admin_client.get("/api/bookings/all")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_get_all_bookings_pagination(admin_client):
    r = await admin_client.get("/api/bookings/all", params={"skip": 0, "limit": 10})
    assert r.status_code == 200


# --- Admin cancel ---


async def test_admin_cancel_booking(
    admin_client, db, seed_user, seed_service, seed_slot, mock_notifications
):
    """Admin can cancel any booking without time restriction."""
    # Create booking directly in DB to avoid client/admin_client override conflict
    booking = Booking(
        client_id=seed_user.id,
        service_id=seed_service.id,
        slot_id=seed_slot.id,
        status=BookingStatus.confirmed,
        remind_before_hours=2,
    )
    seed_slot.status = SlotStatus.booked
    db.add(booking)
    await db.commit()
    await db.refresh(booking)

    r = await admin_client.patch(f"/api/bookings/{booking.id}/admin-cancel")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "cancelled"
    assert data["slot"]["status"] == "available"
    mock_notifications["admin_cancelled"].assert_called_once()
    assert mock_notifications["cancelled"].call_count == 1  # admin notified too


async def test_admin_cancel_already_cancelled(
    admin_client, db, seed_user, seed_service, seed_slot, mock_notifications
):
    booking = Booking(
        client_id=seed_user.id,
        service_id=seed_service.id,
        slot_id=seed_slot.id,
        status=BookingStatus.confirmed,
        remind_before_hours=2,
    )
    seed_slot.status = SlotStatus.booked
    db.add(booking)
    await db.commit()
    await db.refresh(booking)

    await admin_client.patch(f"/api/bookings/{booking.id}/admin-cancel")

    r = await admin_client.patch(f"/api/bookings/{booking.id}/admin-cancel")
    assert r.status_code == 400


async def test_admin_cancel_nonexistent(admin_client, mock_notifications):
    r = await admin_client.patch("/api/bookings/9999/admin-cancel")
    assert r.status_code == 404


async def test_admin_cancel_non_admin(client, mock_notifications):
    """Regular user cannot use admin-cancel."""
    r = await client.patch("/api/bookings/1/admin-cancel")
    assert r.status_code == 403


# --- Admin reschedule ---


async def test_admin_reschedule_success(
    admin_client, db, seed_user, seed_service, seed_slot, seed_slot_2, mock_notifications
):
    """Admin reschedules a confirmed booking to a new slot."""
    # Create confirmed booking on seed_slot (mark slot as booked)
    booking = Booking(
        client_id=seed_user.id,
        service_id=seed_service.id,
        slot_id=seed_slot.id,
        status=BookingStatus.confirmed,
        remind_before_hours=2,
    )
    seed_slot.status = SlotStatus.booked
    db.add(booking)
    await db.commit()
    await db.refresh(booking)

    old_slot_id = seed_slot.id
    new_slot_id = seed_slot_2.id

    r = await admin_client.patch(
        f"/api/bookings/{booking.id}/admin-reschedule",
        json={"new_slot_id": new_slot_id},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["slot"]["id"] == new_slot_id
    assert data["slot"]["date"] == "2026-12-26"

    # reminded should be reset
    await db.refresh(booking)
    assert booking.reminded is False

    # Old slot should be available again
    await db.refresh(seed_slot)
    assert seed_slot.status == SlotStatus.available

    # New slot should be booked
    await db.refresh(seed_slot_2)
    assert seed_slot_2.status == SlotStatus.booked

    # Both reschedule notifications called
    mock_notifications["client_rescheduled"].assert_called_once()
    mock_notifications["admins_rescheduled"].assert_called_once()


async def test_admin_reschedule_non_admin(client, mock_notifications):
    """Regular user cannot use admin-reschedule."""
    r = await client.patch(
        "/api/bookings/1/admin-reschedule",
        json={"new_slot_id": 1},
    )
    assert r.status_code == 403


async def test_admin_reschedule_nonexistent_booking(admin_client, mock_notifications):
    """Reschedule nonexistent booking → 404."""
    r = await admin_client.patch(
        "/api/bookings/99999/admin-reschedule",
        json={"new_slot_id": 1},
    )
    assert r.status_code == 404


async def test_admin_reschedule_cancelled_booking(
    admin_client, db, seed_user, seed_service, seed_slot, seed_slot_2, mock_notifications
):
    """Cannot reschedule a cancelled booking."""
    booking = Booking(
        client_id=seed_user.id,
        service_id=seed_service.id,
        slot_id=seed_slot.id,
        status=BookingStatus.cancelled,
        remind_before_hours=2,
    )
    db.add(booking)
    await db.commit()
    await db.refresh(booking)

    r = await admin_client.patch(
        f"/api/bookings/{booking.id}/admin-reschedule",
        json={"new_slot_id": seed_slot_2.id},
    )
    assert r.status_code == 400
    assert "подтверждённую" in r.json()["detail"]


async def test_admin_reschedule_completed_booking(
    admin_client, db, seed_user, seed_service, seed_slot, seed_slot_2, mock_notifications
):
    """Cannot reschedule a completed booking."""
    booking = Booking(
        client_id=seed_user.id,
        service_id=seed_service.id,
        slot_id=seed_slot.id,
        status=BookingStatus.completed,
        remind_before_hours=2,
    )
    db.add(booking)
    await db.commit()
    await db.refresh(booking)

    r = await admin_client.patch(
        f"/api/bookings/{booking.id}/admin-reschedule",
        json={"new_slot_id": seed_slot_2.id},
    )
    assert r.status_code == 400
    assert "подтверждённую" in r.json()["detail"]


async def test_admin_reschedule_same_slot(
    admin_client, db, seed_user, seed_service, seed_slot, mock_notifications
):
    """Cannot reschedule to the same slot."""
    booking = Booking(
        client_id=seed_user.id,
        service_id=seed_service.id,
        slot_id=seed_slot.id,
        status=BookingStatus.confirmed,
        remind_before_hours=2,
    )
    seed_slot.status = SlotStatus.booked
    db.add(booking)
    await db.commit()
    await db.refresh(booking)

    r = await admin_client.patch(
        f"/api/bookings/{booking.id}/admin-reschedule",
        json={"new_slot_id": seed_slot.id},
    )
    assert r.status_code == 400
    assert "совпадает" in r.json()["detail"]


async def test_admin_reschedule_slot_booked(
    admin_client, db, seed_user, seed_service, seed_slot, seed_slot_2, mock_notifications
):
    """Cannot reschedule to a slot that is already booked."""
    booking = Booking(
        client_id=seed_user.id,
        service_id=seed_service.id,
        slot_id=seed_slot.id,
        status=BookingStatus.confirmed,
        remind_before_hours=2,
    )
    seed_slot.status = SlotStatus.booked
    seed_slot_2.status = SlotStatus.booked
    db.add(booking)
    await db.commit()
    await db.refresh(booking)

    r = await admin_client.patch(
        f"/api/bookings/{booking.id}/admin-reschedule",
        json={"new_slot_id": seed_slot_2.id},
    )
    assert r.status_code == 400
    assert "недоступен" in r.json()["detail"]


async def test_admin_reschedule_slot_blocked(
    admin_client, db, seed_user, seed_service, seed_slot, seed_slot_2, mock_notifications
):
    """Cannot reschedule to a blocked slot."""
    booking = Booking(
        client_id=seed_user.id,
        service_id=seed_service.id,
        slot_id=seed_slot.id,
        status=BookingStatus.confirmed,
        remind_before_hours=2,
    )
    seed_slot.status = SlotStatus.booked
    seed_slot_2.status = SlotStatus.blocked
    db.add(booking)
    await db.commit()
    await db.refresh(booking)

    r = await admin_client.patch(
        f"/api/bookings/{booking.id}/admin-reschedule",
        json={"new_slot_id": seed_slot_2.id},
    )
    assert r.status_code == 400
    assert "недоступен" in r.json()["detail"]


async def test_admin_reschedule_slot_not_found(
    admin_client, db, seed_user, seed_service, seed_slot, mock_notifications
):
    """Cannot reschedule to a nonexistent slot."""
    booking = Booking(
        client_id=seed_user.id,
        service_id=seed_service.id,
        slot_id=seed_slot.id,
        status=BookingStatus.confirmed,
        remind_before_hours=2,
    )
    seed_slot.status = SlotStatus.booked
    db.add(booking)
    await db.commit()
    await db.refresh(booking)

    r = await admin_client.patch(
        f"/api/bookings/{booking.id}/admin-reschedule",
        json={"new_slot_id": 99999},
    )
    assert r.status_code == 404
    assert "слот" in r.json()["detail"].lower()
