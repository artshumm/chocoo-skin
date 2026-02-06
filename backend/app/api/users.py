from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.models import User, UserRole
from app.schemas.schemas import UserAuth, UserResponse

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("/auth", response_model=UserResponse)
async def auth_user(data: UserAuth, db: AsyncSession = Depends(get_db)):
    """Регистрация или логин через Telegram ID. Возвращает пользователя."""
    result = await db.execute(select(User).where(User.telegram_id == data.telegram_id))
    user = result.scalar_one_or_none()

    if user:
        # Обновляем данные если изменились
        changed = False
        if data.username and user.username != data.username:
            user.username = data.username
            changed = True
        if data.first_name and user.first_name != data.first_name:
            user.first_name = data.first_name
            changed = True
        # Синхронизируем роль с ADMIN_IDS при каждом входе
        expected_role = UserRole.admin if data.telegram_id in settings.admin_id_list else UserRole.client
        if user.role != expected_role:
            user.role = expected_role
            changed = True
        if changed:
            await db.commit()
            await db.refresh(user)
        return user

    # Новый пользователь
    role = UserRole.admin if data.telegram_id in settings.admin_id_list else UserRole.client
    user = User(
        telegram_id=data.telegram_id,
        username=data.username,
        first_name=data.first_name,
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
