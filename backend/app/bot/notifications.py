import asyncio
import logging

from app.bot.bot_instance import bot
from app.core.config import settings

logger = logging.getLogger(__name__)

SEND_TIMEOUT = 10.0  # секунд на одно сообщение


def _format_client_info(
    first_name: str | None,
    username: str | None,
    phone: str | None,
) -> str:
    """Форматирует информацию о клиенте для уведомлений админам."""
    # Имя (@username) или fallback
    if first_name and username:
        name_line = f"Клиент: {first_name} (@{username})"
    elif first_name:
        name_line = f"Клиент: {first_name}"
    elif username:
        name_line = f"Клиент: @{username}"
    else:
        name_line = "Клиент: (не указан)"

    lines = [name_line]
    if phone:
        lines.append(f"Телефон: {phone}")

    return "\n".join(lines)


async def notify_admins_new_booking(
    first_name: str | None,
    username: str | None,
    phone: str | None,
    service_name: str,
    slot_date: str,
    slot_time: str,
) -> None:
    """Уведомляет всех админов о новой записи."""
    client_info = _format_client_info(first_name, username, phone)
    text = (
        f"📋 Новая запись!\n\n"
        f"{client_info}\n"
        f"Услуга: {service_name}\n"
        f"Дата: {slot_date}\n"
        f"Время: {slot_time}"
    )
    await _send_to_admins(text)


async def notify_admins_cancelled_booking(
    first_name: str | None,
    username: str | None,
    phone: str | None,
    service_name: str,
    slot_date: str,
    slot_time: str,
) -> None:
    """Уведомляет всех админов об отмене записи."""
    client_info = _format_client_info(first_name, username, phone)
    text = (
        f"❌ Отмена записи\n\n"
        f"{client_info}\n"
        f"Услуга: {service_name}\n"
        f"Дата: {slot_date}\n"
        f"Время: {slot_time}"
    )
    await _send_to_admins(text)


async def notify_client_booking_confirmed(
    telegram_id: int,
    service_name: str,
    slot_date: str,
    slot_time: str,
    remind_before_hours: int,
) -> None:
    """Отправляет клиенту подтверждение записи."""
    text = (
        f"✅ Вы записаны!\n\n"
        f"Услуга: {service_name}\n"
        f"Дата: {slot_date}\n"
        f"Время: {slot_time}\n"
        f"Напоминание: за {remind_before_hours} ч. до сеанса"
    )
    try:
        await asyncio.wait_for(
            bot.send_message(chat_id=telegram_id, text=text),
            timeout=SEND_TIMEOUT,
        )
    except Exception as e:
        logger.warning("Failed to send confirmation to client %s: %s", telegram_id, e)


async def notify_client_booking_cancelled_by_admin(
    telegram_id: int,
    service_name: str,
    slot_date: str,
    slot_time: str,
) -> None:
    """Уведомляет клиента об отмене записи администратором."""
    text = (
        f"Ваша запись отменена администратором.\n\n"
        f"Услуга: {service_name}\n"
        f"Дата: {slot_date}\n"
        f"Время: {slot_time}\n\n"
        f"Для повторной записи откройте приложение."
    )
    try:
        await asyncio.wait_for(
            bot.send_message(chat_id=telegram_id, text=text),
            timeout=SEND_TIMEOUT,
        )
    except Exception as e:
        logger.warning("Failed to send cancellation to client %s: %s", telegram_id, e)


async def notify_client_post_session(
    telegram_id: int,
    service_name: str,
) -> None:
    """Отправляет клиенту сообщение после сеанса (спасибо + повторная запись)."""
    text = (
        f"Спасибо за визит! 🙏\n\n"
        f"Надеемся, вам понравился сеанс «{service_name}».\n"
        f"Для повторной записи откройте приложение."
    )
    try:
        await asyncio.wait_for(
            bot.send_message(chat_id=telegram_id, text=text),
            timeout=SEND_TIMEOUT,
        )
    except Exception as e:
        logger.warning("Failed to send post-session msg to %s: %s", telegram_id, e)


async def _send_to_admins(text: str) -> None:
    """Отправляет сообщение всем админам. Ошибки логируются, не прерывают работу."""
    for admin_id in settings.admin_id_list:
        try:
            await asyncio.wait_for(
                bot.send_message(chat_id=admin_id, text=text),
                timeout=SEND_TIMEOUT,
            )
        except Exception as e:
            logger.warning("Failed to send notification to admin %s: %s", admin_id, e)
