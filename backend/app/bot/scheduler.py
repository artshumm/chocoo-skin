import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.bot.bot_instance import bot
from app.core.config import settings
from app.core.database import async_session
from app.models.models import Booking, BookingStatus, Slot, User, UserRole

logger = logging.getLogger(__name__)

# Europe/Minsk = UTC+3
MINSK_TZ = timezone(timedelta(hours=3))

# Защита от повторной утренней сводки (in-memory, но с DB-проверкой при старте)
_last_summary_date: str | None = None


async def run_scheduler() -> None:
    """Основной цикл планировщика. Проверяет каждые 60 сек."""
    global _last_summary_date

    # Защита от дублей утренней сводки после рестарта:
    # Если стартуем после 8:01, считаем что сводка уже была отправлена сегодня
    now = datetime.now(MINSK_TZ)
    if now.hour > 8 or (now.hour == 8 and now.minute > 1):
        _last_summary_date = now.strftime("%Y-%m-%d")
        logger.info("Scheduler started after 8:01, skipping today's summary")

    logger.info("Scheduler started")
    while True:
        # Задачи бегут параллельно — падение одной не блокирует остальные
        results = await asyncio.gather(
            _check_reminders(),
            _check_morning_summary(),
            _auto_complete_bookings(),
            return_exceptions=True,
        )
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                task_names = ["_check_reminders", "_check_morning_summary", "_auto_complete_bookings"]
                logger.error("Scheduler %s error: %s", task_names[i], result)

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
                # Сначала помечаем как отправленное (защита от дублей при рестарте/повторе)
                booking.reminded = True
                await db.commit()

                text = (
                    f"⏰ Напоминание!\n\n"
                    f"У вас запись сегодня:\n"
                    f"Услуга: {booking.service.name}\n"
                    f"Время: {slot.start_time.strftime('%H:%M')}\n\n"
                    f"Ждём вас!"
                )
                try:
                    await asyncio.wait_for(
                        bot.send_message(
                            chat_id=booking.client.telegram_id, text=text
                        ),
                        timeout=10.0,
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

    async with async_session() as db:
        today_date = now_minsk.date()
        result = await db.execute(
            select(Booking)
            .join(Slot)
            .join(User, Booking.client_id == User.id)
            .where(
                and_(
                    Slot.date == today_date,
                    Booking.status == BookingStatus.confirmed,
                    User.role != UserRole.admin,
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
        messages = [f"☀️ Доброе утро!\n\nНа сегодня ({today_str}) записей нет."]
    else:
        header = f"☀️ Доброе утро!\n\nЗаписи на сегодня ({today_str}):\n"
        footer = f"\nВсего: {len(bookings)}"
        booking_lines = []
        for i, b in enumerate(bookings, 1):
            client_name = (
                b.client.first_name or b.client.username or str(b.client.telegram_id)
            )
            booking_lines.append(
                f"{i}. {b.slot.start_time.strftime('%H:%M')} — "
                f"{client_name}, {b.service.name}"
            )

        # Telegram limit: 4096 chars. Разбиваем на части если слишком длинное.
        messages = []
        current = header
        for line in booking_lines:
            if len(current) + len(line) + len(footer) + 1 > 4000:
                messages.append(current.rstrip())
                current = ""
            current += line + "\n"
        current += footer
        messages.append(current)

    for admin_id in settings.admin_id_list:
        for msg in messages:
            try:
                await asyncio.wait_for(
                    bot.send_message(chat_id=admin_id, text=msg),
                    timeout=10.0,
                )
            except Exception as e:
                logger.warning("Failed to send morning summary to admin %s: %s", admin_id, e)

    # Ставим флаг ПОСЛЕ отправки, чтобы retry был возможен при ошибке
    _last_summary_date = today_str
    logger.info("Morning summary sent for %s (%d bookings)", today_str, len(bookings))


async def _auto_complete_bookings() -> None:
    """Автозавершение записей после окончания услуги (start_time + duration)."""
    now_minsk = datetime.now(MINSK_TZ)

    async with async_session() as db:
        # Фильтр по дате: только сегодня и ранее (не грузим будущие)
        result = await db.execute(
            select(Booking)
            .join(Slot)
            .where(
                and_(
                    Booking.status == BookingStatus.confirmed,
                    Slot.date <= now_minsk.date(),
                )
            )
            .options(
                selectinload(Booking.slot),
                selectinload(Booking.service),
            )
        )
        bookings = result.scalars().all()

        completed_count = 0
        for booking in bookings:
            slot = booking.slot
            appointment_dt = datetime.combine(
                slot.date, slot.start_time, tzinfo=MINSK_TZ
            )
            # Завершаем после окончания услуги (start + duration)
            end_dt = appointment_dt + timedelta(minutes=booking.service.duration_minutes)
            if end_dt <= now_minsk:
                booking.status = BookingStatus.completed
                completed_count += 1

        if completed_count:
            await db.commit()
            logger.info("Auto-completed %d past bookings", completed_count)
