"""POST /api/demo/reset — полный сброс демо-данных и пересоздание с выбранным пресетом."""

import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import (
    Booking,
    BookingStatus,
    Expense,
    FaqItem,
    SalonInfo,
    ScheduleTemplate,
    Service,
    Slot,
    SlotStatus,
    User,
    UserRole,
)

from demo.backend.presets import GENERIC_FAQ, PRESETS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/demo", tags=["demo"])

MINSK_TZ = timezone(timedelta(hours=3))

# Фиксированные ID для демо-пользователей
DEMO_CLIENT_TG_ID = 1000001
DEMO_ADMIN_TG_ID = 1000002


# ---------------------------------------------------------------------------
# Request schema
# ---------------------------------------------------------------------------
class CustomPreset(BaseModel):
    """Кастомный пресет от пользователя (кнопка «Своё»)."""

    name: str
    address: str = "г. Минск, ул. Примерная, д. 1"
    phone: str = "+375291234567"
    services: list[dict[str, Any]]  # [{name, price, duration_minutes}]


class ResetRequest(BaseModel):
    """Тело запроса /api/demo/reset."""

    preset: Optional[str] = None
    custom: Optional[CustomPreset] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _generate_slots_for_day(
    target_date: date,
    start_hour: int,
    end_hour: int,
    interval_minutes: int,
) -> list[Slot]:
    """Генерирует список Slot-объектов для одного дня.

    Для ночных заведений (end_hour < start_hour) генерирует слоты
    до полуночи (23:59).
    """
    slots: list[Slot] = []

    # Ночные заведения: end_hour < start_hour → генерируем до 23:59
    effective_end_minutes = (
        end_hour * 60 if end_hour > start_hour else 24 * 60
    )

    current_minutes = start_hour * 60
    while current_minutes + interval_minutes <= effective_end_minutes:
        slot_end = current_minutes + interval_minutes
        # Безопасность: не выходим за 23:59
        if slot_end > 23 * 60 + 59:
            break

        slots.append(
            Slot(
                date=target_date,
                start_time=time(current_minutes // 60, current_minutes % 60),
                end_time=time(slot_end // 60, slot_end % 60),
                status=SlotStatus.available,
            )
        )
        current_minutes = slot_end

    return slots


def _build_salon(data: dict[str, Any]) -> SalonInfo:
    return SalonInfo(
        name=data["name"],
        description=data.get("description", ""),
        address=data.get("address", ""),
        phone=data.get("phone", ""),
        working_hours_text=data.get("working_hours_text", ""),
        instagram=data.get("instagram", ""),
        preparation_text=data.get("preparation_text", ""),
    )


def _build_services(items: list[dict[str, Any]]) -> list[Service]:
    services: list[Service] = []
    for item in items:
        services.append(
            Service(
                name=item["name"],
                short_description=item.get("short_description", ""),
                description=item.get("description", ""),
                duration_minutes=item.get("duration_minutes", 30),
                price=item.get("price", 0),
                is_active=True,
            )
        )
    return services


def _build_faq(items: list[dict[str, Any]]) -> list[FaqItem]:
    return [
        FaqItem(
            question=item["question"],
            answer=item["answer"],
            order_index=item.get("order_index", idx),
        )
        for idx, item in enumerate(items)
    ]


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------
@router.post("/reset")
async def reset_demo(
    body: ResetRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Полный сброс демо-данных и пересоздание с выбранным пресетом.

    Удаляет ВСЕ данные из БД, затем заполняет заново:
    - 2 пользователя (клиент + админ)
    - salon_info, services, faq
    - слоты на 14 дней вперёд
    - 3 демо-записи на завтра
    """
    # ── Validate input ────────────────────────────────────────────────
    preset_name: str = "custom"

    if body.preset and body.custom:
        raise HTTPException(
            status_code=400,
            detail="Укажите либо preset, либо custom, но не оба.",
        )

    if body.preset:
        if body.preset not in PRESETS:
            raise HTTPException(
                status_code=400,
                detail=f"Неизвестный пресет: {body.preset}. Доступные: {', '.join(PRESETS.keys())}",
            )
        preset_name = body.preset
    elif not body.custom:
        raise HTTPException(
            status_code=400,
            detail="Укажите preset (название пресета) или custom (свои данные).",
        )

    # ── 1. Delete ALL data (correct FK order) ─────────────────────────
    await db.execute(delete(Booking))
    await db.execute(delete(Slot))
    await db.execute(delete(Service))
    await db.execute(delete(FaqItem))
    await db.execute(delete(SalonInfo))
    await db.execute(delete(User))
    await db.execute(delete(Expense))
    await db.execute(delete(ScheduleTemplate))
    await db.flush()

    logger.info("Demo reset: all tables cleared")

    # ── 2. Create demo users ──────────────────────────────────────────
    client_user = User(
        telegram_id=DEMO_CLIENT_TG_ID,
        username="demo_client",
        first_name="Клиент",
        phone="+375290000001",
        role=UserRole.client,
        consent_given=True,
        consent_date=datetime.now(MINSK_TZ),
    )
    admin_user = User(
        telegram_id=DEMO_ADMIN_TG_ID,
        username="demo_admin",
        first_name="Админ",
        phone="+375290000002",
        role=UserRole.admin,
        consent_given=True,
        consent_date=datetime.now(MINSK_TZ),
    )
    db.add_all([client_user, admin_user])
    await db.flush()

    # ── 3. Insert salon_info ──────────────────────────────────────────
    if body.preset:
        preset_data = PRESETS[body.preset]
        salon = _build_salon(preset_data["salon_data"])
    else:
        # Custom preset
        custom = body.custom  # guaranteed not None
        salon = SalonInfo(
            name=custom.name,
            description=f"Добро пожаловать в {custom.name}!",
            address=custom.address,
            phone=custom.phone,
            working_hours_text="09:00–21:00",
            instagram="",
            preparation_text="",
        )
    db.add(salon)
    await db.flush()

    # ── 4. Insert services ────────────────────────────────────────────
    if body.preset:
        services = _build_services(preset_data["services_data"])
    else:
        custom = body.custom
        services = _build_services(
            [
                {
                    "name": s.get("name", "Услуга"),
                    "short_description": s.get("name", "Услуга"),
                    "description": "",
                    "duration_minutes": s.get("duration_minutes", 30),
                    "price": s.get("price", 0),
                }
                for s in custom.services
            ]
            if custom.services
            else [
                {
                    "name": "Услуга",
                    "short_description": "Базовая услуга",
                    "description": "",
                    "duration_minutes": 30,
                    "price": 0,
                }
            ]
        )
    db.add_all(services)
    await db.flush()

    # ── 5. Insert FAQ ─────────────────────────────────────────────────
    if body.preset:
        faq_items = _build_faq(preset_data["faq_data"])
    else:
        faq_items = _build_faq(GENERIC_FAQ)
    db.add_all(faq_items)
    await db.flush()

    # ── 6. Generate slots for 14 days ─────────────────────────────────
    today = datetime.now(MINSK_TZ).date()

    if body.preset:
        wh = preset_data["working_hours"]
        start_hour = wh["start_hour"]
        end_hour = wh["end_hour"]
        interval = preset_data["slot_interval_minutes"]
    else:
        start_hour = 9
        end_hour = 21
        interval = 30

    all_slots: list[Slot] = []
    for day_offset in range(14):
        target_date = today + timedelta(days=day_offset)
        day_slots = _generate_slots_for_day(
            target_date, start_hour, end_hour, interval
        )
        all_slots.extend(day_slots)

    db.add_all(all_slots)
    await db.flush()

    logger.info(
        "Demo reset: generated %d slots for 14 days (interval=%d min)",
        len(all_slots),
        interval,
    )

    # ── 7. Create 3 demo bookings for tomorrow ───────────────────────
    tomorrow = today + timedelta(days=1)
    tomorrow_slots = [s for s in all_slots if s.date == tomorrow]

    bookings_created = 0
    first_service = services[0] if services else None

    if first_service and len(tomorrow_slots) >= 3:
        for i in range(3):
            slot = tomorrow_slots[i]
            slot.status = SlotStatus.booked

            booking = Booking(
                client_id=client_user.id,
                service_id=first_service.id,
                slot_id=slot.id,
                status=BookingStatus.confirmed,
            )
            db.add(booking)
            bookings_created += 1

    await db.commit()

    logger.info(
        "Demo reset complete: preset=%s, services=%d, slots=%d, bookings=%d",
        preset_name,
        len(services),
        len(all_slots),
        bookings_created,
    )

    return {"status": "ok", "preset": preset_name}
