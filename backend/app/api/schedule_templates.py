from fastapi import APIRouter, Depends
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.models import ScheduleTemplate
from app.schemas.schemas import (
    ScheduleTemplateBulk,
    ScheduleTemplateResponse,
)

router = APIRouter(prefix="/api/schedule-templates", tags=["schedule-templates"])


@router.get("/", response_model=list[ScheduleTemplateResponse])
async def get_templates(
    _admin: int = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Возвращает все шаблоны расписания (0-6 записей)."""
    result = await db.execute(
        select(ScheduleTemplate).order_by(ScheduleTemplate.day_of_week)
    )
    return result.scalars().all()


@router.put("/", response_model=list[ScheduleTemplateResponse])
async def upsert_templates(
    data: ScheduleTemplateBulk,
    _admin: int = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Полностью заменяет шаблоны расписания (bulk upsert)."""
    # Проверяем уникальность дней в запросе
    days = [t.day_of_week for t in data.templates]
    if len(days) != len(set(days)):
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Дублирование дней недели")

    # Удаляем все старые шаблоны и вставляем новые
    await db.execute(delete(ScheduleTemplate))
    for t in data.templates:
        db.add(
            ScheduleTemplate(
                day_of_week=t.day_of_week,
                start_time=t.start_time,
                end_time=t.end_time,
                interval_minutes=t.interval_minutes,
                is_active=t.is_active,
            )
        )
    await db.commit()

    result = await db.execute(
        select(ScheduleTemplate).order_by(ScheduleTemplate.day_of_week)
    )
    return result.scalars().all()
