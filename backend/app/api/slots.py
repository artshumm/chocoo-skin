from datetime import date, time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.models import Slot, SlotStatus
from app.schemas.schemas import SlotCreate, SlotResponse, SlotUpdate

router = APIRouter(prefix="/api/slots", tags=["slots"])


@router.get("/", response_model=list[SlotResponse])
async def get_slots(
    date: date = Query(..., description="Дата в формате YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
):
    """Свободные слоты на указанную дату (для клиента)."""
    result = await db.execute(
        select(Slot)
        .where(Slot.date == date, Slot.status == SlotStatus.available)
        .order_by(Slot.start_time)
    )
    return result.scalars().all()


@router.get("/all", response_model=list[SlotResponse])
async def get_all_slots(
    date: date = Query(..., description="Дата в формате YYYY-MM-DD"),
    _admin: int = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Все слоты на дату — для админа (включая booked и blocked)."""
    result = await db.execute(
        select(Slot).where(Slot.date == date).order_by(Slot.start_time)
    )
    return result.scalars().all()


@router.post("/generate", response_model=list[SlotResponse])
async def generate_slots(
    data: SlotCreate,
    _admin: int = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Админ генерирует слоты на день (например, с 9:00 до 21:00 по 30 мин)."""
    # Проверим что слоты на эту дату ещё не созданы
    existing = await db.execute(select(Slot).where(Slot.date == data.date).limit(1))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400, detail=f"Слоты на {data.date} уже существуют"
        )

    slots = []
    current_minutes = data.start_hour * 60
    end_minutes_limit = data.end_hour * 60

    while current_minutes + data.interval_minutes <= end_minutes_limit:
        slot_end = current_minutes + data.interval_minutes
        # Cap at 23:59 to avoid time overflow
        if slot_end > 23 * 60 + 59:
            break

        slot = Slot(
            date=data.date,
            start_time=time(current_minutes // 60, current_minutes % 60),
            end_time=time(slot_end // 60, slot_end % 60),
            status=SlotStatus.available,
        )
        db.add(slot)
        slots.append(slot)

        current_minutes = slot_end

    await db.commit()
    for s in slots:
        await db.refresh(s)
    return slots


@router.patch("/{slot_id}", response_model=SlotResponse)
async def update_slot(
    slot_id: int,
    data: SlotUpdate,
    _admin: int = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Админ блокирует/разблокирует слот."""
    slot = await db.get(Slot, slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="Слот не найден")

    if data.status not in ("available", "blocked"):
        raise HTTPException(
            status_code=400, detail="Допустимые статусы: available, blocked"
        )

    if slot.status == SlotStatus.booked and data.status != "booked":
        raise HTTPException(
            status_code=400, detail="Нельзя изменить забронированный слот"
        )

    slot.status = SlotStatus(data.status)
    await db.commit()
    await db.refresh(slot)
    return slot
