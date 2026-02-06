from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_admin
from app.bot.notifications import (
    notify_admins_cancelled_booking,
    notify_admins_new_booking,
    notify_client_booking_confirmed,
)
from app.core.database import get_db
from app.models.models import Booking, BookingStatus, Service, Slot, SlotStatus, User
from app.schemas.schemas import BookingCreate, BookingResponse

router = APIRouter(prefix="/api/bookings", tags=["bookings"])

# Салон в Минске (UTC+3)
MINSK_TZ = timezone(timedelta(hours=3))
CANCEL_MIN_HOURS = 10


@router.post("/", response_model=BookingResponse)
async def create_booking(data: BookingCreate, db: AsyncSession = Depends(get_db)):
    """Клиент записывается на свободный слот."""
    # Проверяем пользователя
    result = await db.execute(select(User).where(User.telegram_id == data.telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден. Сначала вызовите /api/users/auth")

    # Проверяем услугу
    service = await db.get(Service, data.service_id)
    if not service or not service.is_active:
        raise HTTPException(status_code=404, detail="Услуга не найдена")

    # Проверяем слот (с блокировкой строки для предотвращения race condition)
    result = await db.execute(
        select(Slot).where(Slot.id == data.slot_id).with_for_update()
    )
    slot = result.scalar_one_or_none()
    if not slot:
        raise HTTPException(status_code=404, detail="Слот не найден")
    if slot.status != SlotStatus.available:
        raise HTTPException(status_code=400, detail="Слот уже занят или заблокирован")

    # Создаём запись
    booking = Booking(
        client_id=user.id,
        service_id=data.service_id,
        slot_id=data.slot_id,
        status=BookingStatus.confirmed,
        remind_before_hours=data.remind_before_hours,
    )
    slot.status = SlotStatus.booked

    db.add(booking)
    await db.commit()

    # Загружаем связи для ответа
    result = await db.execute(
        select(Booking)
        .where(Booking.id == booking.id)
        .options(
            selectinload(Booking.client),
            selectinload(Booking.service),
            selectinload(Booking.slot),
        )
    )
    booking = result.scalar_one()

    # Уведомляем админов
    await notify_admins_new_booking(
        first_name=booking.client.first_name,
        username=booking.client.username,
        phone=booking.client.phone,
        service_name=booking.service.name,
        slot_date=str(booking.slot.date),
        slot_time=booking.slot.start_time.strftime("%H:%M"),
    )

    # Подтверждение клиенту
    await notify_client_booking_confirmed(
        telegram_id=booking.client.telegram_id,
        service_name=booking.service.name,
        slot_date=str(booking.slot.date),
        slot_time=booking.slot.start_time.strftime("%H:%M"),
        remind_before_hours=booking.remind_before_hours,
    )

    return booking


@router.get("/my", response_model=list[BookingResponse])
async def get_my_bookings(
    telegram_id: int = Query(..., description="Telegram ID клиента"),
    db: AsyncSession = Depends(get_db),
):
    """Записи клиента."""
    result = await db.execute(
        select(Booking)
        .join(User)
        .where(User.telegram_id == telegram_id)
        .options(
            selectinload(Booking.client),
            selectinload(Booking.service),
            selectinload(Booking.slot),
        )
        .order_by(Booking.created_at.desc())
    )
    return result.scalars().all()


@router.patch("/{booking_id}/cancel", response_model=BookingResponse)
async def cancel_booking(
    booking_id: int,
    telegram_id: int = Query(..., description="Telegram ID клиента"),
    db: AsyncSession = Depends(get_db),
):
    """Клиент отменяет свою запись. Минимум за 10 часов до начала."""
    result = await db.execute(
        select(Booking)
        .join(User)
        .where(Booking.id == booking_id, User.telegram_id == telegram_id)
        .options(
            selectinload(Booking.client),
            selectinload(Booking.service),
            selectinload(Booking.slot),
        )
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    if booking.status == BookingStatus.cancelled:
        raise HTTPException(status_code=400, detail="Запись уже отменена")

    # Проверка: минимум 10 часов до начала записи
    now_minsk = datetime.now(MINSK_TZ).replace(tzinfo=None)
    slot_dt = datetime.combine(booking.slot.date, booking.slot.start_time)
    time_until = slot_dt - now_minsk
    if time_until < timedelta(hours=CANCEL_MIN_HOURS):
        raise HTTPException(
            status_code=400,
            detail=f"Отмена возможна не позднее чем за {CANCEL_MIN_HOURS} часов до записи",
        )

    booking.status = BookingStatus.cancelled
    booking.slot.status = SlotStatus.available

    await db.commit()
    await db.refresh(booking)

    # Перезагружаем с relations
    result = await db.execute(
        select(Booking)
        .where(Booking.id == booking.id)
        .options(
            selectinload(Booking.client),
            selectinload(Booking.service),
            selectinload(Booking.slot),
        )
    )
    booking = result.scalar_one()

    # Уведомляем админов
    await notify_admins_cancelled_booking(
        first_name=booking.client.first_name,
        username=booking.client.username,
        phone=booking.client.phone,
        service_name=booking.service.name,
        slot_date=str(booking.slot.date),
        slot_time=booking.slot.start_time.strftime("%H:%M"),
    )

    return booking


@router.get("/all", response_model=list[BookingResponse])
async def get_all_bookings(
    _admin: int = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Все записи — для админа."""
    result = await db.execute(
        select(Booking)
        .options(
            selectinload(Booking.client),
            selectinload(Booking.service),
            selectinload(Booking.slot),
        )
        .order_by(Booking.created_at.desc())
    )
    return result.scalars().all()
