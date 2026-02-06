import logging

from app.bot.bot_instance import bot
from app.core.config import settings

logger = logging.getLogger(__name__)


async def notify_admins_new_booking(
    client_name: str,
    service_name: str,
    slot_date: str,
    slot_time: str,
) -> None:
    """Уведомляет всех админов о новой записи."""
    text = (
        f"📋 Новая запись!\n\n"
        f"Клиент: {client_name}\n"
        f"Услуга: {service_name}\n"
        f"Дата: {slot_date}\n"
        f"Время: {slot_time}"
    )
    await _send_to_admins(text)


async def notify_admins_cancelled_booking(
    client_name: str,
    service_name: str,
    slot_date: str,
    slot_time: str,
) -> None:
    """Уведомляет всех админов об отмене записи."""
    text = (
        f"❌ Отмена записи\n\n"
        f"Клиент: {client_name}\n"
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
        await bot.send_message(chat_id=telegram_id, text=text)
    except Exception as e:
        logger.warning("Failed to send confirmation to client %s: %s", telegram_id, e)


async def _send_to_admins(text: str) -> None:
    """Отправляет сообщение всем админам. Ошибки логируются, не прерывают работу."""
    for admin_id in settings.admin_id_list:
        try:
            await bot.send_message(chat_id=admin_id, text=text)
        except Exception as e:
            logger.warning("Failed to send notification to admin %s: %s", admin_id, e)
