from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.models import User, UserRole
from app.schemas.schemas import UserAuth, UserProfileUpdate, UserResponse

router = APIRouter(prefix="/api/users", tags=["users"])

MINSK_TZ = timezone(timedelta(hours=3))


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


@router.patch("/profile", response_model=UserResponse)
async def update_profile(
    data: UserProfileUpdate,
    x_telegram_id: int = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """Клиент обновляет имя, телефон и согласие на обработку ПД."""
    if not data.consent_given:
        raise HTTPException(status_code=400, detail="Необходимо дать согласие на обработку персональных данных")

    result = await db.execute(select(User).where(User.telegram_id == x_telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    user.first_name = data.first_name
    user.phone = data.phone
    user.consent_given = True
    user.consent_date = datetime.now(MINSK_TZ).replace(tzinfo=None)
    await db.commit()
    await db.refresh(user)
    return user
