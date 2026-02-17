"""Tests for scheduler tasks (app.bot.scheduler).

Covers all 5 scheduler tasks:
- _check_reminders
- _check_morning_summary
- _auto_complete_bookings
- _auto_generate_slots
- _check_post_session_feedback
"""

from datetime import date, datetime, time, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.models import (
    Booking,
    BookingStatus,
    SalonInfo,
    ScheduleTemplate,
    Service,
    Slot,
    SlotStatus,
    User,
)
from tests.conftest import TestSession

MINSK_TZ = timezone(timedelta(hours=3))


# ── Controllable datetime ──────────────────────────────────────────


class FakeDatetime(datetime):
    """datetime subclass with controllable now(). combine() still works."""

    _fake_now: datetime | None = None

    @classmethod
    def now(cls, tz=None):
        if cls._fake_now is not None:
            return cls._fake_now
        return datetime.now(tz)


# ── Fixtures ───────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_scheduler_globals():
    """Reset module-level guards between tests."""
    import app.bot.scheduler as sched

    sched._last_summary_date = None
    sched._last_autogen_date = None
    yield
    sched._last_summary_date = None
    sched._last_autogen_date = None
    FakeDatetime._fake_now = None


@pytest_asyncio.fixture
async def seed_reminder_data(db):
    """Confirmed booking tomorrow at 14:00, remind 1h before."""
    user = User(
        telegram_id=99999, username="client", first_name="Client",
        consent_given=True, phone="+375290000000",
    )
    service = Service(
        name="Загар", short_description="s", description="d",
        duration_minutes=20, price=50.0, is_active=True,
    )
    tomorrow = date.today() + timedelta(days=1)
    slot = Slot(
        date=tomorrow, start_time=time(14, 0), end_time=time(14, 20),
        status=SlotStatus.booked,
    )
    salon = SalonInfo(
        name="Salon", description="d", address="ул. Тестовая, 1",
        phone="+375290000001", working_hours_text="9-21",
    )
    db.add_all([user, service, slot, salon])
    await db.commit()
    await db.refresh(user)
    await db.refresh(service)
    await db.refresh(slot)

    booking = Booking(
        client_id=user.id, service_id=service.id, slot_id=slot.id,
        status=BookingStatus.confirmed, remind_before_hours=1,
        reminded=False, feedback_sent=False,
    )
    db.add(booking)
    await db.commit()
    await db.refresh(booking)

    return {"user": user, "service": service, "slot": slot, "booking": booking, "salon": salon}


@pytest_asyncio.fixture
async def seed_completed_booking(db):
    """Completed booking from yesterday."""
    user = User(
        telegram_id=88888, username="done_client", first_name="Done",
        consent_given=True, phone="+375290000002",
    )
    service = Service(
        name="Автозагар", short_description="s", description="d",
        duration_minutes=20, price=40.0, is_active=True,
    )
    yesterday = date.today() - timedelta(days=1)
    slot = Slot(
        date=yesterday, start_time=time(10, 0), end_time=time(10, 20),
        status=SlotStatus.booked,
    )
    db.add_all([user, service, slot])
    await db.commit()
    await db.refresh(user)
    await db.refresh(service)
    await db.refresh(slot)

    booking = Booking(
        client_id=user.id, service_id=service.id, slot_id=slot.id,
        status=BookingStatus.completed, remind_before_hours=1,
        reminded=True, feedback_sent=False,
    )
    db.add(booking)
    await db.commit()
    await db.refresh(booking)

    return {"user": user, "service": service, "slot": slot, "booking": booking}


# ── Mock helpers ───────────────────────────────────────────────────


def _mock_bot():
    mock = MagicMock()
    mock.send_message = AsyncMock()
    return mock


def _mock_settings(admin_ids=None):
    mock = MagicMock()
    mock.admin_id_list = admin_ids or [446746688]
    return mock


def _set_fake_now(dt: datetime):
    FakeDatetime._fake_now = dt


# ══════════════════════════════════════════════════════════════════
#  _check_reminders
# ══════════════════════════════════════════════════════════════════


class TestCheckReminders:

    async def test_sends_reminder_within_threshold(self, db, seed_reminder_data):
        """Reminder sent when booking is within remind_before_hours."""
        data = seed_reminder_data
        slot = data["slot"]

        # 30 min before appointment → within 1h threshold
        fake_now = datetime.combine(slot.date, slot.start_time, tzinfo=MINSK_TZ) - timedelta(minutes=30)
        _set_fake_now(fake_now)

        mock_bot = _mock_bot()

        with (
            patch("app.bot.scheduler.async_session", TestSession),
            patch("app.bot.scheduler.bot", mock_bot),
            patch("app.bot.scheduler.datetime", FakeDatetime),
        ):
            from app.bot.scheduler import _check_reminders
            await _check_reminders()

        mock_bot.send_message.assert_called_once()
        call_kwargs = mock_bot.send_message.call_args
        assert call_kwargs.kwargs["chat_id"] == data["user"].telegram_id
        assert "Напоминание" in call_kwargs.kwargs["text"]

    async def test_no_reminder_outside_threshold(self, db, seed_reminder_data):
        """No reminder when appointment is far in the future."""
        data = seed_reminder_data
        slot = data["slot"]

        # 3 hours before → outside 1h threshold
        fake_now = datetime.combine(slot.date, slot.start_time, tzinfo=MINSK_TZ) - timedelta(hours=3)
        _set_fake_now(fake_now)

        mock_bot = _mock_bot()

        with (
            patch("app.bot.scheduler.async_session", TestSession),
            patch("app.bot.scheduler.bot", mock_bot),
            patch("app.bot.scheduler.datetime", FakeDatetime),
        ):
            from app.bot.scheduler import _check_reminders
            await _check_reminders()

        mock_bot.send_message.assert_not_called()

    async def test_no_reminder_already_reminded(self, db, seed_reminder_data):
        """No reminder when booking.reminded is already True."""
        data = seed_reminder_data
        slot = data["slot"]

        # Mark as already reminded
        data["booking"].reminded = True
        db.add(data["booking"])
        await db.commit()

        fake_now = datetime.combine(slot.date, slot.start_time, tzinfo=MINSK_TZ) - timedelta(minutes=30)
        _set_fake_now(fake_now)

        mock_bot = _mock_bot()

        with (
            patch("app.bot.scheduler.async_session", TestSession),
            patch("app.bot.scheduler.bot", mock_bot),
            patch("app.bot.scheduler.datetime", FakeDatetime),
        ):
            from app.bot.scheduler import _check_reminders
            await _check_reminders()

        mock_bot.send_message.assert_not_called()

    async def test_reminder_includes_salon_address(self, db, seed_reminder_data):
        """Reminder message includes salon address."""
        data = seed_reminder_data
        slot = data["slot"]

        fake_now = datetime.combine(slot.date, slot.start_time, tzinfo=MINSK_TZ) - timedelta(minutes=30)
        _set_fake_now(fake_now)

        mock_bot = _mock_bot()

        with (
            patch("app.bot.scheduler.async_session", TestSession),
            patch("app.bot.scheduler.bot", mock_bot),
            patch("app.bot.scheduler.datetime", FakeDatetime),
        ):
            from app.bot.scheduler import _check_reminders
            await _check_reminders()

        text = mock_bot.send_message.call_args.kwargs["text"]
        assert "ул. Тестовая, 1" in text


# ══════════════════════════════════════════════════════════════════
#  _check_morning_summary
# ══════════════════════════════════════════════════════════════════


class TestCheckMorningSummary:

    async def test_sends_summary_at_8am(self, db, seed_reminder_data):
        """Summary sent at 8:00 Minsk time."""
        data = seed_reminder_data
        slot = data["slot"]

        # Set to 8:00 on the day of the slot
        summary_time = datetime.combine(slot.date, time(8, 0), tzinfo=MINSK_TZ)
        _set_fake_now(summary_time)

        mock_bot = _mock_bot()
        mock_settings = _mock_settings([446746688])

        with (
            patch("app.bot.scheduler.async_session", TestSession),
            patch("app.bot.scheduler.bot", mock_bot),
            patch("app.bot.scheduler.datetime", FakeDatetime),
            patch("app.bot.scheduler.settings", mock_settings),
        ):
            from app.bot.scheduler import _check_morning_summary
            await _check_morning_summary()

        mock_bot.send_message.assert_called()
        text = mock_bot.send_message.call_args.kwargs["text"]
        assert "Доброе утро" in text

    async def test_no_summary_outside_window(self, db, seed_reminder_data):
        """No summary sent outside 8:00-8:01 window."""
        data = seed_reminder_data
        slot = data["slot"]

        # Set to 10:00 → outside window
        wrong_time = datetime.combine(slot.date, time(10, 0), tzinfo=MINSK_TZ)
        _set_fake_now(wrong_time)

        mock_bot = _mock_bot()

        with (
            patch("app.bot.scheduler.async_session", TestSession),
            patch("app.bot.scheduler.bot", mock_bot),
            patch("app.bot.scheduler.datetime", FakeDatetime),
        ):
            from app.bot.scheduler import _check_morning_summary
            await _check_morning_summary()

        mock_bot.send_message.assert_not_called()

    async def test_no_duplicate_summary(self, db, seed_reminder_data):
        """Second call on the same day does not re-send."""
        data = seed_reminder_data
        slot = data["slot"]

        summary_time = datetime.combine(slot.date, time(8, 0), tzinfo=MINSK_TZ)
        _set_fake_now(summary_time)

        mock_bot = _mock_bot()
        mock_settings = _mock_settings([446746688])

        with (
            patch("app.bot.scheduler.async_session", TestSession),
            patch("app.bot.scheduler.bot", mock_bot),
            patch("app.bot.scheduler.datetime", FakeDatetime),
            patch("app.bot.scheduler.settings", mock_settings),
        ):
            from app.bot.scheduler import _check_morning_summary
            await _check_morning_summary()
            mock_bot.send_message.reset_mock()

            # Second call → should not send
            await _check_morning_summary()

        mock_bot.send_message.assert_not_called()

    async def test_summary_no_bookings(self, db):
        """Summary says 'no bookings' when none exist."""
        today = date.today()
        summary_time = datetime.combine(today, time(8, 0), tzinfo=MINSK_TZ)
        _set_fake_now(summary_time)

        mock_bot = _mock_bot()
        mock_settings = _mock_settings([446746688])

        with (
            patch("app.bot.scheduler.async_session", TestSession),
            patch("app.bot.scheduler.bot", mock_bot),
            patch("app.bot.scheduler.datetime", FakeDatetime),
            patch("app.bot.scheduler.settings", mock_settings),
        ):
            from app.bot.scheduler import _check_morning_summary
            await _check_morning_summary()

        text = mock_bot.send_message.call_args.kwargs["text"]
        assert "записей нет" in text


# ══════════════════════════════════════════════════════════════════
#  _auto_complete_bookings
# ══════════════════════════════════════════════════════════════════


class TestAutoCompleteBookings:

    async def test_completes_past_booking(self, db, seed_reminder_data):
        """Booking completed when past start_time + duration."""
        data = seed_reminder_data
        slot = data["slot"]

        # Set "now" to 1 hour after the slot
        past_time = datetime.combine(slot.date, slot.start_time, tzinfo=MINSK_TZ) + timedelta(hours=1)
        _set_fake_now(past_time)

        with (
            patch("app.bot.scheduler.async_session", TestSession),
            patch("app.bot.scheduler.datetime", FakeDatetime),
        ):
            from app.bot.scheduler import _auto_complete_bookings
            await _auto_complete_bookings()

        # Verify booking is completed
        async with TestSession() as session:
            result = await session.execute(
                select(Booking).where(Booking.id == data["booking"].id)
            )
            booking = result.scalar_one()
            assert booking.status == BookingStatus.completed

    async def test_no_complete_future_booking(self, db, seed_reminder_data):
        """Booking stays confirmed when still in the future."""
        data = seed_reminder_data
        slot = data["slot"]

        # Set "now" to 1 hour BEFORE the slot
        future_time = datetime.combine(slot.date, slot.start_time, tzinfo=MINSK_TZ) - timedelta(hours=1)
        _set_fake_now(future_time)

        with (
            patch("app.bot.scheduler.async_session", TestSession),
            patch("app.bot.scheduler.datetime", FakeDatetime),
        ):
            from app.bot.scheduler import _auto_complete_bookings
            await _auto_complete_bookings()

        async with TestSession() as session:
            result = await session.execute(
                select(Booking).where(Booking.id == data["booking"].id)
            )
            booking = result.scalar_one()
            assert booking.status == BookingStatus.confirmed

    async def test_7day_lookback_limit(self, db):
        """Bookings older than 7 days are not auto-completed."""
        user = User(
            telegram_id=77777, username="old", first_name="Old",
            consent_given=True, phone="+375290000003",
        )
        service = Service(
            name="Old", short_description="s", description="d",
            duration_minutes=20, price=30.0, is_active=True,
        )
        old_date = date.today() - timedelta(days=10)
        slot = Slot(
            date=old_date, start_time=time(10, 0), end_time=time(10, 20),
            status=SlotStatus.booked,
        )
        db.add_all([user, service, slot])
        await db.commit()
        await db.refresh(user)
        await db.refresh(service)
        await db.refresh(slot)

        booking = Booking(
            client_id=user.id, service_id=service.id, slot_id=slot.id,
            status=BookingStatus.confirmed, remind_before_hours=1,
            reminded=True, feedback_sent=False,
        )
        db.add(booking)
        await db.commit()
        await db.refresh(booking)

        # "Now" is today, booking is 10 days old → outside 7-day window
        _set_fake_now(datetime.combine(date.today(), time(12, 0), tzinfo=MINSK_TZ))

        with (
            patch("app.bot.scheduler.async_session", TestSession),
            patch("app.bot.scheduler.datetime", FakeDatetime),
        ):
            from app.bot.scheduler import _auto_complete_bookings
            await _auto_complete_bookings()

        async with TestSession() as session:
            result = await session.execute(
                select(Booking).where(Booking.id == booking.id)
            )
            b = result.scalar_one()
            assert b.status == BookingStatus.confirmed  # NOT completed


# ══════════════════════════════════════════════════════════════════
#  _auto_generate_slots
# ══════════════════════════════════════════════════════════════════


class TestAutoGenerateSlots:

    async def test_generates_slots_from_template(self, db):
        """Slots generated from active schedule template."""
        today = date.today()
        # Find the weekday of tomorrow so we can create a template for it
        tomorrow = today + timedelta(days=1)
        weekday = tomorrow.weekday()

        template = ScheduleTemplate(
            day_of_week=weekday,
            start_time=time(10, 0), end_time=time(11, 0),
            interval_minutes=20, is_active=True,
        )
        db.add(template)
        await db.commit()

        # Set time to 7:00 today
        gen_time = datetime.combine(today, time(7, 0), tzinfo=MINSK_TZ)
        _set_fake_now(gen_time)

        with (
            patch("app.bot.scheduler.async_session", TestSession),
            patch("app.bot.scheduler.datetime", FakeDatetime),
        ):
            from app.bot.scheduler import _auto_generate_slots
            await _auto_generate_slots()

        # Verify slots were created for tomorrow
        async with TestSession() as session:
            result = await session.execute(
                select(Slot).where(Slot.date == tomorrow)
            )
            slots = result.scalars().all()
            assert len(slots) == 3  # 10:00-10:20, 10:20-10:40, 10:40-11:00

    async def test_skips_dates_with_existing_slots(self, db):
        """No slots generated for dates that already have slots."""
        today = date.today()
        tomorrow = today + timedelta(days=1)
        weekday = tomorrow.weekday()

        template = ScheduleTemplate(
            day_of_week=weekday,
            start_time=time(10, 0), end_time=time(11, 0),
            interval_minutes=20, is_active=True,
        )
        # Pre-existing slot on tomorrow
        existing_slot = Slot(
            date=tomorrow, start_time=time(9, 0), end_time=time(9, 20),
            status=SlotStatus.available,
        )
        db.add_all([template, existing_slot])
        await db.commit()

        gen_time = datetime.combine(today, time(7, 0), tzinfo=MINSK_TZ)
        _set_fake_now(gen_time)

        with (
            patch("app.bot.scheduler.async_session", TestSession),
            patch("app.bot.scheduler.datetime", FakeDatetime),
        ):
            from app.bot.scheduler import _auto_generate_slots
            await _auto_generate_slots()

        # Only the pre-existing slot should exist (no new ones)
        async with TestSession() as session:
            result = await session.execute(
                select(Slot).where(Slot.date == tomorrow)
            )
            slots = result.scalars().all()
            assert len(slots) == 1

    async def test_no_templates_skips_generation(self, db):
        """No slots generated when no active templates exist."""
        today = date.today()
        gen_time = datetime.combine(today, time(7, 0), tzinfo=MINSK_TZ)
        _set_fake_now(gen_time)

        with (
            patch("app.bot.scheduler.async_session", TestSession),
            patch("app.bot.scheduler.datetime", FakeDatetime),
        ):
            from app.bot.scheduler import _auto_generate_slots
            await _auto_generate_slots()

        # No slots should exist
        async with TestSession() as session:
            result = await session.execute(select(Slot))
            slots = result.scalars().all()
            assert len(slots) == 0

    async def test_only_runs_at_7am(self, db):
        """Auto-generate returns immediately outside 7:00-7:01."""
        today = date.today()
        template = ScheduleTemplate(
            day_of_week=today.weekday(),
            start_time=time(10, 0), end_time=time(11, 0),
            interval_minutes=20, is_active=True,
        )
        db.add(template)
        await db.commit()

        # Set time to 12:00 → outside window
        wrong_time = datetime.combine(today, time(12, 0), tzinfo=MINSK_TZ)
        _set_fake_now(wrong_time)

        with (
            patch("app.bot.scheduler.async_session", TestSession),
            patch("app.bot.scheduler.datetime", FakeDatetime),
        ):
            from app.bot.scheduler import _auto_generate_slots
            await _auto_generate_slots()

        # No slots generated
        async with TestSession() as session:
            result = await session.execute(select(Slot))
            slots = result.scalars().all()
            assert len(slots) == 0


# ══════════════════════════════════════════════════════════════════
#  _check_post_session_feedback
# ══════════════════════════════════════════════════════════════════


class TestCheckPostSessionFeedback:

    async def test_sends_feedback_after_delay(self, db, seed_completed_booking):
        """Feedback sent 1+ hour after session ends."""
        data = seed_completed_booking
        slot = data["slot"]

        # 2 hours after the session ended
        end_dt = datetime.combine(slot.date, slot.start_time, tzinfo=MINSK_TZ) + timedelta(
            minutes=data["service"].duration_minutes
        )
        fake_now = end_dt + timedelta(hours=2)
        _set_fake_now(fake_now)

        mock_notify = AsyncMock(return_value=True)

        with (
            patch("app.bot.scheduler.async_session", TestSession),
            patch("app.bot.scheduler.datetime", FakeDatetime),
            patch("app.bot.scheduler.notify_client_post_session", mock_notify),
        ):
            from app.bot.scheduler import _check_post_session_feedback
            await _check_post_session_feedback()

        mock_notify.assert_called_once_with(
            telegram_id=data["user"].telegram_id,
            service_name=data["service"].name,
        )

        # Verify feedback_sent is True
        async with TestSession() as session:
            result = await session.execute(
                select(Booking).where(Booking.id == data["booking"].id)
            )
            booking = result.scalar_one()
            assert booking.feedback_sent is True

    async def test_no_feedback_before_delay(self, db, seed_completed_booking):
        """No feedback sent within 1 hour after session."""
        data = seed_completed_booking
        slot = data["slot"]

        # 30 minutes after session ended → before 1h delay
        end_dt = datetime.combine(slot.date, slot.start_time, tzinfo=MINSK_TZ) + timedelta(
            minutes=data["service"].duration_minutes
        )
        fake_now = end_dt + timedelta(minutes=30)
        _set_fake_now(fake_now)

        mock_notify = AsyncMock(return_value=True)

        with (
            patch("app.bot.scheduler.async_session", TestSession),
            patch("app.bot.scheduler.datetime", FakeDatetime),
            patch("app.bot.scheduler.notify_client_post_session", mock_notify),
        ):
            from app.bot.scheduler import _check_post_session_feedback
            await _check_post_session_feedback()

        mock_notify.assert_not_called()

    async def test_feedback_not_marked_on_failure(self, db, seed_completed_booking):
        """feedback_sent stays False when notification fails."""
        data = seed_completed_booking
        slot = data["slot"]

        end_dt = datetime.combine(slot.date, slot.start_time, tzinfo=MINSK_TZ) + timedelta(
            minutes=data["service"].duration_minutes
        )
        fake_now = end_dt + timedelta(hours=2)
        _set_fake_now(fake_now)

        # Simulate failed send
        mock_notify = AsyncMock(return_value=False)

        with (
            patch("app.bot.scheduler.async_session", TestSession),
            patch("app.bot.scheduler.datetime", FakeDatetime),
            patch("app.bot.scheduler.notify_client_post_session", mock_notify),
        ):
            from app.bot.scheduler import _check_post_session_feedback
            await _check_post_session_feedback()

        mock_notify.assert_called_once()

        # feedback_sent should still be False
        async with TestSession() as session:
            result = await session.execute(
                select(Booking).where(Booking.id == data["booking"].id)
            )
            booking = result.scalar_one()
            assert booking.feedback_sent is False

    async def test_no_feedback_already_sent(self, db, seed_completed_booking):
        """No feedback for bookings where feedback_sent is True."""
        data = seed_completed_booking
        slot = data["slot"]

        # Mark feedback as already sent
        data["booking"].feedback_sent = True
        db.add(data["booking"])
        await db.commit()

        end_dt = datetime.combine(slot.date, slot.start_time, tzinfo=MINSK_TZ) + timedelta(
            minutes=data["service"].duration_minutes
        )
        fake_now = end_dt + timedelta(hours=2)
        _set_fake_now(fake_now)

        mock_notify = AsyncMock(return_value=True)

        with (
            patch("app.bot.scheduler.async_session", TestSession),
            patch("app.bot.scheduler.datetime", FakeDatetime),
            patch("app.bot.scheduler.notify_client_post_session", mock_notify),
        ):
            from app.bot.scheduler import _check_post_session_feedback
            await _check_post_session_feedback()

        mock_notify.assert_not_called()
