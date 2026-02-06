from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import Service
from app.schemas.schemas import ServiceResponse

router = APIRouter(prefix="/api/services", tags=["services"])


@router.get("/", response_model=list[ServiceResponse])
async def get_services(db: AsyncSession = Depends(get_db)):
    """Список активных услуг."""
    result = await db.execute(
        select(Service).where(Service.is_active.is_(True)).order_by(Service.id)
    )
    return result.scalars().all()
