import logging

from fastapi import Depends, Header, HTTPException

from app.core.config import settings
from app.core.telegram_auth import TelegramAuthError, validate_init_data

logger = logging.getLogger(__name__)

# Dev-режим: telegram_id для тестов когда валидация отключена
_DEV_USER = {"id": 0, "username": "dev", "first_name": "Developer"}


async def get_telegram_user(authorization: str = Header("")) -> dict:
    """Извлекает и валидирует пользователя из Telegram initData.

    Ожидает заголовок: Authorization: tma <initData>

    Returns:
        dict с id, username, first_name
    """
    if settings.skip_telegram_validation:
        # Dev-режим: если нет заголовка — возвращаем dev-пользователя
        if not authorization:
            logger.warning("Dev mode: no Authorization header, using dev user")
            return _DEV_USER
        # Если заголовок есть — пробуем валидировать, но не падаем
        if authorization.startswith("tma "):
            try:
                return validate_init_data(authorization[4:])
            except TelegramAuthError:
                return _DEV_USER
        return _DEV_USER

    # Production: строгая валидация
    if not authorization.startswith("tma "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header",
        )

    init_data = authorization[4:]
    try:
        return validate_init_data(init_data)
    except TelegramAuthError as e:
        logger.warning("Telegram auth failed: %s", e)
        raise HTTPException(status_code=401, detail="Invalid Telegram authorization")


async def require_admin(tg_user: dict = Depends(get_telegram_user)) -> int:
    """Проверяет что запрос от админа."""
    telegram_id = tg_user["id"]
    if not settings.admin_id_list:
        raise HTTPException(status_code=503, detail="ADMIN_IDS not configured")
    if telegram_id not in settings.admin_id_list:
        raise HTTPException(status_code=403, detail="Admin access required")
    return telegram_id
