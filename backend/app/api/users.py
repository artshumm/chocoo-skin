from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_telegram_user
from app.core.config import settings
from app.core.database import get_db
from app.models.models import User, UserRole
from app.schemas.schemas import UserProfileUpdate, UserResponse

router = APIRouter(prefix="/api/users", tags=["users"])

MINSK_TZ = timezone(timedelta(hours=3))


@router.post("/auth", response_model=UserResponse)
async def auth_user(
    tg_user: dict = Depends(get_telegram_user),
    db: AsyncSession = Depends(get_db),
):
    """Регистрация или логин. Данные берутся из валидированного initData."""
    telegram_id = tg_user["id"]
    username = tg_user.get("username")
    first_name = tg_user.get("first_name")

    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()

    if user:
        changed = False
        if username and user.username != username:
            user.username = username
            changed = True
        if first_name and user.first_name != first_name:
            user.first_name = first_name
            changed = True
        expected_role = UserRole.admin if telegram_id in settings.admin_id_list else UserRole.client
        if user.role != expected_role:
            user.role = expected_role
            changed = True
        if changed:
            await db.commit()
            await db.refresh(user)
        return user

    role = UserRole.admin if telegram_id in settings.admin_id_list else UserRole.client
    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/profile", response_model=UserResponse)
async def update_profile(
    data: UserProfileUpdate,
    tg_user: dict = Depends(get_telegram_user),
    db: AsyncSession = Depends(get_db),
):
    """Клиент обновляет имя, телефон и согласие на обработку ПД."""
    if not data.consent_given:
        raise HTTPException(status_code=400, detail="Необходимо дать согласие на обработку персональных данных")

    telegram_id = tg_user["id"]
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    user.first_name = data.first_name
    user.phone = data.phone
    user.instagram = data.instagram
    user.consent_given = True
    user.consent_date = datetime.now(MINSK_TZ).replace(tzinfo=None)
    await db.commit()
    await db.refresh(user)
    return user
