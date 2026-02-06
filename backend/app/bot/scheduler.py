import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.bot.bot_instance import bot
from app.core.config import settings
from app.core.database import async_session
from app.models.models import Booking, BookingStatus, Slot

logger = logging.getLogger(__name__)

# Europe/Minsk = UTC+3
MINSK_TZ = timezone(timedelta(hours=3))

# Защита от повторной утренней сводки (in-memory)
_last_summary_date: str | None = None


async def run_scheduler() -> None:
    """Основной цикл планировщика. Проверяет каждые 60 сек."""
    logger.info("Scheduler started")
    while True:
        try:
            await _check_reminders()
            await _check_morning_summary()
        except Exception as e:
            logger.error("Scheduler error: %s", e)
        await asyncio.sleep(60)


async def _check_reminders() -> None:
    """Отправляет напоминания клиентам перед записью."""
    now_minsk = datetime.now(MINSK_TZ)

    async with async_session() as db:
        result = await db.execute(
            select(Booking)
            .join(Slot)
            .where(
                and_(
                    Booking.status == BookingStatus.confirmed,
                    Booking.reminded == False,
                )
            )
            .options(
                selectinload(Booking.client),
                selectinload(Booking.service),
                selectinload(Booking.slot),
            )
        )
        bookings = result.scalars().all()

        for booking in bookings:
            slot = booking.slot
            appointment_dt = datetime.combine(
                slot.date, slot.start_time, tzinfo=MINSK_TZ
            )
            time_until = appointment_dt - now_minsk
            remind_threshold = timedelta(hours=booking.remind_before_hours)

            if timedelta(0) < time_until <= remind_threshold:
                text = (
                    f"⏰ Напоминание!\n\n"
                    f"У вас запись сегодня:\n"
                    f"Услуга: {booking.service.name}\n"
                    f"Время: {slot.start_time.strftime('%H:%M')}\n\n"
                    f"Ждём вас!"
                )
                try:
                    await bot.send_message(
                        chat_id=booking.client.telegram_id, text=text
                    )
                    logger.info(
                        "Reminder sent to %s for booking %s",
                        booking.client.telegram_id,
                        booking.id,
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to send reminder to %s: %s",
                        booking.client.telegram_id,
                        e,
                    )

                booking.reminded = True
                await db.commit()


async def _check_morning_summary() -> None:
    """Отправляет админам утреннюю сводку записей на день в 8:00 по Минску."""
    global _last_summary_date

    now_minsk = datetime.now(MINSK_TZ)
    today_str = now_minsk.strftime("%Y-%m-%d")

    # Только в 8:00-8:01 (окно 2 мин для 60-сек цикла)
    if now_minsk.hour != 8 or now_minsk.minute > 1:
        return

    if _last_summary_date == today_str:
        return

    _last_summary_date = today_str

    async with async_session() as db:
        today_date = now_minsk.date()
        result = await db.execute(
            select(Booking)
            .join(Slot)
            .where(
                and_(
                    Slot.date == today_date,
                    Booking.status == BookingStatus.confirmed,
                )
            )
            .options(
                selectinload(Booking.client),
                selectinload(Booking.service),
                selectinload(Booking.slot),
            )
            .order_by(Slot.start_time)
        )
        bookings = result.scalars().all()

    if not bookings:
        text = f"☀️ Доброе утро!\n\nНа сегодня ({today_str}) записей нет."
    else:
        lines = [f"☀️ Доброе утро!\n\nЗаписи на сегодня ({today_str}):\n"]
        for i, b in enumerate(bookings, 1):
            client_name = (
                b.client.first_name or b.client.username or str(b.client.telegram_id)
            )
            lines.append(
                f"{i}. {b.slot.start_time.strftime('%H:%M')} — "
                f"{client_name}, {b.service.name}"
            )
        lines.append(f"\nВсего: {len(bookings)}")
        text = "\n".join(lines)

    for admin_id in settings.admin_id_list:
        try:
            await bot.send_message(chat_id=admin_id, text=text)
        except Exception as e:
            logger.warning("Failed to send morning summary to admin %s: %s", admin_id, e)

    logger.info("Morning summary sent for %s (%d bookings)", today_str, len(bookings))
