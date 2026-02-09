import asyncio
import logging

from app.bot.bot_instance import bot
from app.core.config import settings

logger = logging.getLogger(__name__)

SEND_TIMEOUT = 10.0  # секунд на одно сообщение

# WARNING: все bot.send_message вызовы используют plain text (без parse_mode).
# Если когда-либо добавите parse_mode="HTML", ВСЕ user-controlled строки
# (first_name, username, service_name) ОБЯЗАНЫ быть пропущены через _escape_html.


def _escape_html(text: str) -> str:
    """Escape HTML entities for safe use in Telegram messages with parse_mode=HTML."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

PREPARATION_TEXT = (
    "🔹 накануне вечером или утром (но не менее чем за 6 часов до процедуры) "
    "распарить кожу и проскрабировать все тело, можно использовать мочалку или скраб, "
    "но! обязательно без масел (сахар + гель для душа - отличный вариант; "
    "кофейные и соляные скрабы не используем), после этого не наносим крем на тело\n"
    "🔹 перед процедурой, если есть возможность, следует принять душ без геля, "
    "и не наносить крема и дезодорант\n"
    "🔹 одежда - темных цветов, свободная без перетягивающих элементов"
)


def _format_client_info(
    first_name: str | None,
    username: str | None,
    phone: str | None,
    instagram: str | None = None,
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
    if instagram:
        lines.append(f"Instagram: {instagram}")
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
    instagram: str | None = None,
) -> None:
    """Уведомляет всех админов о новой записи."""
    client_info = _format_client_info(first_name, username, phone, instagram)
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
    instagram: str | None = None,
) -> None:
    """Уведомляет всех админов об отмене записи."""
    client_info = _format_client_info(first_name, username, phone, instagram)
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
    price: float = 0,
    address: str = "",
) -> None:
    """Отправляет клиенту подтверждение записи."""
    lines = [
        f"✅ Вы записаны!\n",
        f"Услуга: {service_name}",
        f"Дата: {slot_date}",
        f"Время: {slot_time}",
        f"Напоминание: за {remind_before_hours} ч. до сеанса",
    ]
    if address:
        lines.append(f"\nАдрес: {address}")
    if price > 0:
        price_str = f"{price:.0f}" if price == int(price) else f"{price:.2f}"
        lines.append(f"Стоимость: {price_str} BYN")
    lines.append(f"\nРекомендации по подготовке:\n{PREPARATION_TEXT}")
    text = "\n".join(lines)
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
) -> bool:
    """Отправляет клиенту сообщение после сеанса. Возвращает True при успехе."""
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
        return True
    except Exception as e:
        logger.warning("Failed to send post-session msg to %s: %s", telegram_id, e)
        return False


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
