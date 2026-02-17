import asyncio
import logging
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.bot.bot_instance import bot
from app.bot.notifications import notify_client_post_session
from app.core.config import settings
from app.core.database import async_session
from app.models.models import Booking, BookingStatus, SalonInfo, ScheduleTemplate, Slot, SlotStatus, User, UserRole

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
            _auto_generate_slots(),
            _check_post_session_feedback(),
            return_exceptions=True,
        )
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                task_names = [
                    "_check_reminders", "_check_morning_summary",
                    "_auto_complete_bookings", "_auto_generate_slots",
                    "_check_post_session_feedback",
                ]
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

        # Загружаем адрес салона (один раз для всех напоминаний)
        salon_result = await db.execute(select(SalonInfo).limit(1))
        salon = salon_result.scalar_one_or_none()
        salon_address = salon.address if salon else ""

        # Collect eligible bookings and build messages
        send_tasks: list[tuple[int, str, int]] = []  # (telegram_id, text, booking_id)
        for booking in bookings:
            slot = booking.slot
            appointment_dt = datetime.combine(
                slot.date, slot.start_time, tzinfo=MINSK_TZ
            )
            time_until = appointment_dt - now_minsk
            remind_threshold = timedelta(hours=booking.remind_before_hours)

            if timedelta(0) < time_until <= remind_threshold:
                # Mark before send (защита от дублей при рестарте)
                booking.reminded = True

                lines = [
                    f"⏰ Напоминание!\n",
                    f"У вас запись сегодня:",
                    f"Услуга: {booking.service.name}",
                    f"Время: {slot.start_time.strftime('%H:%M')}",
                ]
                if salon_address:
                    lines.append(f"\nАдрес: {salon_address}")
                lines.append("\nЖдём вас!")
                send_tasks.append((booking.client.telegram_id, "\n".join(lines), booking.id))

        if not send_tasks:
            return

        # Batch commit all reminded flags before sending
        await db.commit()

        # Send all reminders in parallel
        async def _send_reminder(tid: int, text: str, bid: int) -> None:
            try:
                await asyncio.wait_for(
                    bot.send_message(chat_id=tid, text=text), timeout=10.0,
                )
                logger.info("Reminder sent to %s for booking %s", tid, bid)
            except Exception as e:
                logger.warning("Failed to send reminder to %s: %s", tid, e)

        await asyncio.gather(
            *[_send_reminder(tid, text, bid) for tid, text, bid in send_tasks]
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
                    Slot.date >= now_minsk.date() - timedelta(days=7),
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


FEEDBACK_DELAY_HOURS = 1  # через 1 час после окончания сеанса


async def _check_post_session_feedback() -> None:
    """Отправляет 'Спасибо за визит' через 1 час после окончания сеанса."""
    now_minsk = datetime.now(MINSK_TZ)

    async with async_session() as db:
        result = await db.execute(
            select(Booking)
            .join(Slot)
            .where(
                and_(
                    Booking.status == BookingStatus.completed,
                    Booking.feedback_sent == False,
                    Slot.date <= now_minsk.date(),
                    Slot.date >= now_minsk.date() - timedelta(days=7),
                )
            )
            .options(
                selectinload(Booking.client),
                selectinload(Booking.service),
                selectinload(Booking.slot),
            )
        )
        bookings = result.scalars().all()

        # Collect eligible bookings for parallel sending
        eligible: list[Booking] = []
        for booking in bookings:
            slot = booking.slot
            end_dt = datetime.combine(
                slot.date, slot.start_time, tzinfo=MINSK_TZ
            ) + timedelta(minutes=booking.service.duration_minutes)

            if now_minsk >= end_dt + timedelta(hours=FEEDBACK_DELAY_HOURS):
                eligible.append(booking)

        if not eligible:
            return

        # Send all feedback messages in parallel
        results = await asyncio.gather(
            *[
                notify_client_post_session(
                    telegram_id=b.client.telegram_id,
                    service_name=b.service.name,
                )
                for b in eligible
            ]
        )

        # Mark only successfully sent ones (send-then-mark pattern)
        sent_count = 0
        for booking, sent in zip(eligible, results):
            if sent:
                booking.feedback_sent = True
                sent_count += 1

        if sent_count:
            await db.commit()
            logger.info("Sent %d post-session feedback messages", sent_count)


# Авто-генерация: запускаем раз в день (в 7:00 по Минску)
_last_autogen_date: str | None = None

AUTO_GENERATE_DAYS_AHEAD = 14


async def _auto_generate_slots() -> None:
    """Генерирует слоты на N дней вперёд по шаблонам расписания.

    Запускается раз в день в 7:00 по Минску. Пропускает даты,
    на которые слоты уже существуют.
    """
    global _last_autogen_date

    now_minsk = datetime.now(MINSK_TZ)
    today_str = now_minsk.strftime("%Y-%m-%d")

    # Раз в день, в окне 7:00-7:01
    if now_minsk.hour != 7 or now_minsk.minute > 1:
        return
    if _last_autogen_date == today_str:
        return

    async with async_session() as db:
        # Загружаем активные шаблоны
        result = await db.execute(
            select(ScheduleTemplate).where(ScheduleTemplate.is_active == True)
        )
        templates = {t.day_of_week: t for t in result.scalars().all()}
        if not templates:
            _last_autogen_date = today_str
            logger.warning("No active schedule templates — auto-slot generation skipped")
            return

        today = now_minsk.date()
        total_created = 0

        for offset in range(AUTO_GENERATE_DAYS_AHEAD):
            target_date = today + timedelta(days=offset)
            weekday = target_date.weekday()  # 0=Mon..6=Sun

            template = templates.get(weekday)
            if not template:
                continue

            # Проверяем: есть ли уже слоты на эту дату?
            existing = await db.execute(
                select(Slot.id).where(Slot.date == target_date).limit(1)
            )
            if existing.scalar_one_or_none() is not None:
                continue

            # Генерируем слоты по шаблону
            current_minutes = template.start_time.hour * 60 + template.start_time.minute
            end_minutes = template.end_time.hour * 60 + template.end_time.minute

            while current_minutes + template.interval_minutes <= end_minutes:
                slot_end = current_minutes + template.interval_minutes
                if slot_end > 23 * 60 + 59:
                    break
                db.add(Slot(
                    date=target_date,
                    start_time=time(current_minutes // 60, current_minutes % 60),
                    end_time=time(slot_end // 60, slot_end % 60),
                    status=SlotStatus.available,
                ))
                total_created += 1
                current_minutes = slot_end

        if total_created:
            await db.commit()
            logger.info("Auto-generated %d slots for next %d days", total_created, AUTO_GENERATE_DAYS_AHEAD)

    _last_autogen_date = today_str
