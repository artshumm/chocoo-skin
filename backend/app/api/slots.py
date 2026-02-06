from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.models import Slot, SlotStatus
from app.schemas.schemas import SlotCreate, SlotResponse, SlotUpdate

router = APIRouter(prefix="/api/slots", tags=["slots"])

MINSK_TZ = timezone(timedelta(hours=3))
SLOT_CUTOFF_MINUTES = 30


@router.get("/", response_model=list[SlotResponse])
async def get_slots(
    date: date = Query(..., description="Дата в формате YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
):
    """Свободные слоты на указанную дату (для клиента)."""
    query = select(Slot).where(Slot.date == date, Slot.status == SlotStatus.available)

    # Если дата сегодня — убираем слоты, до которых < 30 мин
    now_minsk = datetime.now(MINSK_TZ)
    if date == now_minsk.date():
        cutoff = (now_minsk + timedelta(minutes=SLOT_CUTOFF_MINUTES)).time()
        query = query.where(Slot.start_time >= cutoff)

    result = await db.execute(query.order_by(Slot.start_time))
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
    # Нельзя генерировать слоты на прошедшие даты
    now_minsk = datetime.now(MINSK_TZ)
    if data.date < now_minsk.date():
        raise HTTPException(status_code=400, detail="Нельзя создавать слоты на прошедшие даты")

    # Проверим что слоты на эту дату ещё не созданы
    existing = await db.execute(select(Slot).where(Slot.date == data.date).limit(1))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400, detail=f"Слоты на {data.date} уже существуют"
        )

    slots = []
    current_minutes = data.start_hour * 60 + data.start_minute
    end_minutes_limit = data.end_hour * 60 + data.end_minute

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

    # Нельзя сделать доступным прошедший слот
    if data.status == "available":
        now_minsk = datetime.now(MINSK_TZ)
        if slot.date == now_minsk.date():
            if slot.start_time <= now_minsk.time():
                raise HTTPException(
                    status_code=400,
                    detail="Нельзя открыть слот, время которого уже прошло",
                )

    slot.status = SlotStatus(data.status)
    await db.commit()
    await db.refresh(slot)
    return slot
