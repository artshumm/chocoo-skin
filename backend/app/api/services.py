from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.models import Service
from app.schemas.schemas import ServiceCreate, ServiceResponse, ServiceUpdate

router = APIRouter(prefix="/api/services", tags=["services"])


@router.get("/", response_model=list[ServiceResponse])
async def get_services(db: AsyncSession = Depends(get_db)):
    """Список активных услуг."""
    result = await db.execute(
        select(Service).where(Service.is_active.is_(True)).order_by(Service.id)
    )
    return result.scalars().all()


@router.get("/all", response_model=list[ServiceResponse])
async def get_all_services(
    admin_id: int = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Все услуги (включая неактивные) — для админа."""
    result = await db.execute(select(Service).order_by(Service.id))
    return result.scalars().all()


@router.post("/", response_model=ServiceResponse, status_code=201)
async def create_service(
    data: ServiceCreate,
    admin_id: int = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = Service(**data.model_dump())
    db.add(service)
    await db.commit()
    await db.refresh(service)
    return service


@router.patch("/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: int,
    data: ServiceUpdate,
    admin_id: int = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(service, key, value)

    await db.commit()
    await db.refresh(service)
    return service


@router.delete("/{service_id}", status_code=204)
async def delete_service(
    service_id: int,
    admin_id: int = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete: деактивирует услугу (is_active=False).

    Не удаляет из БД, чтобы сохранить привязку к существующим записям.
    """
    result = await db.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    service.is_active = False
    await db.commit()
