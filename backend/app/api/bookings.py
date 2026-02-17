from datetime import date, datetime, timedelta, timezone
import logging

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
logger = logging.getLogger(__name__)

# Салон в Минске (UTC+3)
MINSK_TZ = timezone(timedelta(hours=3))
CANCEL_MIN_HOURS = 10

_BOOKING_LOAD_OPTIONS = (
    selectinload(Booking.client),
    selectinload(Booking.service),
    selectinload(Booking.slot),
)


async def _get_verified_user(db: AsyncSession, telegram_id: int) -> User:
    """Загружает пользователя и проверяет что профиль заполнен."""
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден. Сначала вызовите /api/users/auth")
    if not user.consent_given or not user.phone:
        raise HTTPException(status_code=400, detail="Необходимо заполнить профиль перед записью")
    return user


async def _get_available_slot(db: AsyncSession, slot_id: int) -> Slot:
    """Загружает слот с блокировкой и проверяет доступность."""
    result = await db.execute(
        select(Slot).where(Slot.id == slot_id).with_for_update()
    )
    slot = result.scalar_one_or_none()
    if not slot:
        raise HTTPException(status_code=404, detail="Слот не найден")
    if slot.status != SlotStatus.available:
        raise HTTPException(status_code=400, detail="Слот уже занят или заблокирован")

    now_minsk = datetime.now(MINSK_TZ).replace(tzinfo=None)
    slot_dt = datetime.combine(slot.date, slot.start_time)
    if slot_dt - now_minsk < timedelta(hours=1):
        raise HTTPException(status_code=400, detail="Запись возможна минимум за 1 час до начала")
    return slot


async def _load_booking_with_relations(db: AsyncSession, booking_id: int) -> Booking:
    """Загружает booking с client, service, slot."""
    result = await db.execute(
        select(Booking)
        .where(Booking.id == booking_id)
        .options(*_BOOKING_LOAD_OPTIONS)
    )
    return result.scalar_one()


async def _send_new_booking_notifications(booking: Booking, db: AsyncSession) -> None:
    """Отправляет уведомления о новой записи (админам + клиенту)."""
    try:
        await notify_admins_new_booking(
            first_name=booking.client.first_name,
            username=booking.client.username,
            phone=booking.client.phone,
            service_name=booking.service.name,
            slot_date=str(booking.slot.date),
            slot_time=booking.slot.start_time.strftime("%H:%M"),
            instagram=booking.client.instagram,
        )
    except Exception as e:
        logger.error("Failed to notify admins about new booking %d: %s", booking.id, e)

    # Загружаем адрес салона для уведомления клиента
    try:
        salon_result = await db.execute(select(SalonInfo).limit(1))
        salon = salon_result.scalar_one_or_none()
        salon_address = salon.address if salon else ""
        salon_prep_text = salon.preparation_text if salon else ""
    except Exception as e:
        logger.error("Failed to load salon info for notification: %s", e)
        salon_address = ""
        salon_prep_text = ""

    try:
        await notify_client_booking_confirmed(
            telegram_id=booking.client.telegram_id,
            service_name=booking.service.name,
            slot_date=str(booking.slot.date),
            slot_time=booking.slot.start_time.strftime("%H:%M"),
            remind_before_hours=booking.remind_before_hours,
            price=float(booking.service.price),
            address=salon_address,
            preparation_text=salon_prep_text,
        )
    except Exception as e:
        logger.error("Failed to notify client %d about booking: %s", booking.client.telegram_id, e)


async def _cancel_and_release_slot(booking: Booking, db: AsyncSession) -> Booking:
    """Общая логика отмены: меняет статус, освобождает слот, коммитит."""
    booking.status = BookingStatus.cancelled

    # Восстанавливаем слот только если он был забронирован
    slot_result = await db.execute(
        select(Slot).where(Slot.id == booking.slot_id).with_for_update()
    )
    slot = slot_result.scalar_one_or_none()
    if slot and slot.status == SlotStatus.booked:
        slot.status = SlotStatus.available

    await db.commit()
    return await _load_booking_with_relations(db, booking.id)


async def _send_cancel_notifications(booking: Booking, by_admin: bool = False) -> None:
    """Уведомления при отмене записи."""
    if by_admin:
        try:
            await notify_client_booking_cancelled_by_admin(
                telegram_id=booking.client.telegram_id,
                service_name=booking.service.name,
                slot_date=str(booking.slot.date),
                slot_time=booking.slot.start_time.strftime("%H:%M"),
            )
        except Exception as e:
            logger.error("Failed to notify client %d about admin cancellation: %s", booking.client.telegram_id, e)

    try:
        await notify_admins_cancelled_booking(
            first_name=booking.client.first_name,
            username=booking.client.username,
            phone=booking.client.phone,
            service_name=booking.service.name,
            slot_date=str(booking.slot.date),
            slot_time=booking.slot.start_time.strftime("%H:%M"),
            instagram=booking.client.instagram,
        )
    except Exception as e:
        logger.error("Failed to notify admins about cancelled booking %d: %s", booking.id, e)


def _validate_cancellable(booking: Booking) -> None:
    """Проверяет что запись можно отменить."""
    if booking.status == BookingStatus.cancelled:
        raise HTTPException(status_code=400, detail="Запись уже отменена")
    if booking.status == BookingStatus.completed:
        raise HTTPException(status_code=400, detail="Завершённую запись нельзя отменить")


@router.post("/", response_model=BookingResponse)
async def create_booking(
    data: BookingCreate,
    tg_user: dict = Depends(get_telegram_user),
    db: AsyncSession = Depends(get_db),
) -> BookingResponse:
    """Клиент записывается на свободный слот. telegram_id из initData."""
    user = await _get_verified_user(db, tg_user["id"])

    service = await db.get(Service, data.service_id)
    if not service or not service.is_active:
        raise HTTPException(status_code=404, detail="Услуга не найдена")

    slot = await _get_available_slot(db, data.slot_id)

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

    booking = await _load_booking_with_relations(db, booking.id)
    await _send_new_booking_notifications(booking, db)
    return booking


@router.get("/my", response_model=list[BookingResponse])
async def get_my_bookings(
    tg_user: dict = Depends(get_telegram_user),
    db: AsyncSession = Depends(get_db),
) -> list[BookingResponse]:
    """Записи клиента."""
    telegram_id = tg_user["id"]
    result = await db.execute(
        select(Booking)
        .join(User)
        .where(User.telegram_id == telegram_id)
        .options(*_BOOKING_LOAD_OPTIONS)
        .order_by(Booking.created_at.desc())
    )
    return result.scalars().all()


@router.patch("/{booking_id}/cancel", response_model=BookingResponse)
async def cancel_booking(
    booking_id: int,
    tg_user: dict = Depends(get_telegram_user),
    db: AsyncSession = Depends(get_db),
) -> BookingResponse:
    """Клиент отменяет свою запись. Минимум за 10 часов до начала."""
    telegram_id = tg_user["id"]
    result = await db.execute(
        select(Booking)
        .join(User)
        .where(Booking.id == booking_id, User.telegram_id == telegram_id)
        .options(*_BOOKING_LOAD_OPTIONS)
        .with_for_update()
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    _validate_cancellable(booking)

    # Проверка: минимум 10 часов до начала записи
    now_minsk = datetime.now(MINSK_TZ).replace(tzinfo=None)
    slot_dt = datetime.combine(booking.slot.date, booking.slot.start_time)
    if slot_dt - now_minsk < timedelta(hours=CANCEL_MIN_HOURS):
        raise HTTPException(
            status_code=400,
            detail=f"Отмена возможна не позднее чем за {CANCEL_MIN_HOURS} часов до записи",
        )

    booking = await _cancel_and_release_slot(booking, db)
    await _send_cancel_notifications(booking)
    return booking


@router.patch("/{booking_id}/admin-cancel", response_model=BookingResponse)
async def admin_cancel_booking(
    booking_id: int,
    _admin: int = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> BookingResponse:
    """Админ отменяет запись клиента (без ограничения по времени)."""
    result = await db.execute(
        select(Booking)
        .where(Booking.id == booking_id)
        .options(*_BOOKING_LOAD_OPTIONS)
        .with_for_update()
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    _validate_cancellable(booking)

    booking = await _cancel_and_release_slot(booking, db)
    await _send_cancel_notifications(booking, by_admin=True)
    return booking


@router.get("/all", response_model=list[BookingResponse])
async def get_all_bookings(
    filter_date: date | None = Query(None, alias="date"),
    status: str | None = Query(None, pattern="^(confirmed|cancelled|completed|pending)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    _admin: int = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[BookingResponse]:
    """Все записи — для админа (с фильтрами и пагинацией)."""
    query = (
        select(Booking)
        .join(Slot)
        .options(*_BOOKING_LOAD_OPTIONS)
    )
    if filter_date is not None:
        query = query.where(Slot.date == filter_date)
    if status is not None:
        query = query.where(Booking.status == status)

    query = query.order_by(Booking.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()
