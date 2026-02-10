from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_telegram_user, require_admin
from app.bot.notifications import (
    notify_admins_cancelled_booking,
    notify_admins_new_booking,
    notify_client_booking_cancelled_by_admin,
    notify_client_booking_confirmed,
)
from app.core.database import get_db
from app.models.models import Booking, BookingStatus, SalonInfo, Service, Slot, SlotStatus, User
from app.schemas.schemas import BookingCreate, BookingResponse

router = APIRouter(prefix="/api/bookings", tags=["bookings"])

# Салон в Минске (UTC+3)
MINSK_TZ = timezone(timedelta(hours=3))
CANCEL_MIN_HOURS = 10


@router.post("/", response_model=BookingResponse)
async def create_booking(
    data: BookingCreate,
    tg_user: dict = Depends(get_telegram_user),
    db: AsyncSession = Depends(get_db),
):
    """Клиент записывается на свободный слот. telegram_id из initData."""
    telegram_id = tg_user["id"]

    # Проверяем пользователя
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден. Сначала вызовите /api/users/auth")

    # Проверяем профиль (согласие + телефон)
    if not user.consent_given or not user.phone:
        raise HTTPException(status_code=400, detail="Необходимо заполнить профиль перед записью")

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

    # Проверка: минимум 1 час до начала слота
    now_minsk = datetime.now(MINSK_TZ).replace(tzinfo=None)
    slot_dt = datetime.combine(slot.date, slot.start_time)
    if slot_dt - now_minsk < timedelta(hours=1):
        raise HTTPException(status_code=400, detail="Запись возможна минимум за 1 час до начала")

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
        instagram=booking.client.instagram,
    )

    # Загружаем адрес салона для уведомления
    salon_result = await db.execute(select(SalonInfo).limit(1))
    salon = salon_result.scalar_one_or_none()

    # Подтверждение клиенту
    await notify_client_booking_confirmed(
        telegram_id=booking.client.telegram_id,
        service_name=booking.service.name,
        slot_date=str(booking.slot.date),
        slot_time=booking.slot.start_time.strftime("%H:%M"),
        remind_before_hours=booking.remind_before_hours,
        price=float(booking.service.price),
        address=salon.address if salon else "",
        preparation_text=salon.preparation_text if salon else "",
    )

    return booking


@router.get("/my", response_model=list[BookingResponse])
async def get_my_bookings(
    tg_user: dict = Depends(get_telegram_user),
    db: AsyncSession = Depends(get_db),
):
    """Записи клиента."""
    telegram_id = tg_user["id"]
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
    tg_user: dict = Depends(get_telegram_user),
    db: AsyncSession = Depends(get_db),
):
    """Клиент отменяет свою запись. Минимум за 10 часов до начала."""
    telegram_id = tg_user["id"]
    # with_for_update() предотвращает race condition при двойной отмене
    result = await db.execute(
        select(Booking)
        .join(User)
        .where(Booking.id == booking_id, User.telegram_id == telegram_id)
        .options(
            selectinload(Booking.client),
            selectinload(Booking.service),
            selectinload(Booking.slot),
        )
        .with_for_update()
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    if booking.status == BookingStatus.cancelled:
        raise HTTPException(status_code=400, detail="Запись уже отменена")
    if booking.status == BookingStatus.completed:
        raise HTTPException(status_code=400, detail="Завершённую запись нельзя отменить")

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
    # Восстанавливаем слот только если он был забронирован (не если админ заблокировал)
    if booking.slot.status == SlotStatus.booked:
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
        instagram=booking.client.instagram,
    )

    return booking


@router.patch("/{booking_id}/admin-cancel", response_model=BookingResponse)
async def admin_cancel_booking(
    booking_id: int,
    _admin: int = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Админ отменяет запись клиента (без ограничения по времени)."""
    result = await db.execute(
        select(Booking)
        .where(Booking.id == booking_id)
        .options(
            selectinload(Booking.client),
            selectinload(Booking.service),
            selectinload(Booking.slot),
        )
        .with_for_update()
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    if booking.status == BookingStatus.cancelled:
        raise HTTPException(status_code=400, detail="Запись уже отменена")
    if booking.status == BookingStatus.completed:
        raise HTTPException(status_code=400, detail="Завершённую запись нельзя отменить")

    booking.status = BookingStatus.cancelled
    if booking.slot.status == SlotStatus.booked:
        booking.slot.status = SlotStatus.available

    await db.commit()

    # Reload with relations
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

    # Уведомляем клиента
    await notify_client_booking_cancelled_by_admin(
        telegram_id=booking.client.telegram_id,
        service_name=booking.service.name,
        slot_date=str(booking.slot.date),
        slot_time=booking.slot.start_time.strftime("%H:%M"),
    )

    # Уведомляем админов
    await notify_admins_cancelled_booking(
        first_name=booking.client.first_name,
        username=booking.client.username,
        phone=booking.client.phone,
        service_name=booking.service.name,
        slot_date=str(booking.slot.date),
        slot_time=booking.slot.start_time.strftime("%H:%M"),
        instagram=booking.client.instagram,
    )

    return booking


@router.get("/all", response_model=list[BookingResponse])
async def get_all_bookings(
    filter_date: date | None = Query(None, alias="date"),
    status: str | None = Query(None, pattern="^(confirmed|cancelled|completed|pending)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    _admin: int = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Все записи — для админа (с фильтрами и пагинацией)."""
    query = (
        select(Booking)
        .join(Slot)
        .options(
            selectinload(Booking.client),
            selectinload(Booking.service),
            selectinload(Booking.slot),
        )
    )
    if filter_date is not None:
        query = query.where(Slot.date == filter_date)
    if status is not None:
        query = query.where(Booking.status == status)

    query = query.order_by(Booking.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()
