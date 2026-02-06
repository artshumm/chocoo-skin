from fastapi import Header, HTTPException

from app.core.config import settings


async def require_admin(x_telegram_id: int = Header(...)) -> int:
    """Проверяет что запрос от админа (по Telegram ID в заголовке)."""
    if not settings.admin_id_list:
        raise HTTPException(status_code=503, detail="ADMIN_IDS not configured")
    if x_telegram_id not in settings.admin_id_list:
        raise HTTPException(status_code=403, detail="Admin access required")
    return x_telegram_id
