"""Telegram Mini App initData validation (HMAC-SHA256).

See: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qs, unquote

from app.core.config import settings

# initData считается действительной 24 часа
AUTH_DATE_MAX_AGE_SECONDS = 24 * 60 * 60


class TelegramAuthError(Exception):
    """Ошибка валидации Telegram initData."""


def validate_init_data(init_data: str) -> dict:
    """Валидирует initData и возвращает данные пользователя.

    Returns:
        dict с ключами: id, username, first_name (из Telegram user)

    Raises:
        TelegramAuthError при невалидных данных.
    """
    if not init_data:
        raise TelegramAuthError("initData is empty")

    # Парсим query string
    parsed = parse_qs(init_data, keep_blank_values=True)

    # Извлекаем hash
    received_hash = parsed.pop("hash", [None])[0]
    if not received_hash:
        raise TelegramAuthError("hash not found in initData")

    # Проверяем auth_date
    auth_date_str = parsed.get("auth_date", [None])[0]
    if not auth_date_str:
        raise TelegramAuthError("auth_date not found in initData")

    try:
        auth_date = int(auth_date_str)
    except ValueError:
        raise TelegramAuthError("invalid auth_date")

    age = int(time.time()) - auth_date
    if age > AUTH_DATE_MAX_AGE_SECONDS:
        raise TelegramAuthError(f"initData expired ({age}s > {AUTH_DATE_MAX_AGE_SECONDS}s)")

    if age < -60:  # допускаем 60 сек расхождения часов
        raise TelegramAuthError("auth_date is in the future")

    # Формируем data-check-string (отсортированные key=value через \n)
    data_check_parts = []
    for key in sorted(parsed.keys()):
        val = parsed[key][0]
        data_check_parts.append(f"{key}={val}")
    data_check_string = "\n".join(data_check_parts)

    # HMAC-SHA256: secret_key = HMAC("WebAppData", bot_token)
    secret_key = hmac.new(
        b"WebAppData", settings.bot_token.encode(), hashlib.sha256
    ).digest()

    # computed_hash = HMAC(data_check_string, secret_key)
    computed_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise TelegramAuthError("invalid signature")

    # Извлекаем user
    user_json = parsed.get("user", [None])[0]
    if not user_json:
        raise TelegramAuthError("user not found in initData")

    try:
        user_data = json.loads(unquote(user_json))
    except (json.JSONDecodeError, TypeError):
        raise TelegramAuthError("invalid user JSON")

    user_id = user_data.get("id")
    if not user_id:
        raise TelegramAuthError("user.id not found")

    return {
        "id": int(user_id),
        "username": user_data.get("username"),
        "first_name": user_data.get("first_name"),
    }
