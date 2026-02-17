from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.models import FaqItem, SalonInfo
from app.schemas.schemas import FaqCreate, FaqReorder, FaqResponse, FaqUpdate, SalonUpdate

router = APIRouter(prefix="/api", tags=["salon"])


@router.get("/salon")
async def get_salon_info(db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(select(SalonInfo).limit(1))
    salon = result.scalar_one_or_none()
    if not salon:
        return {
            "name": "Салон",
            "description": "",
            "address": "",
            "phone": "",
            "working_hours_text": "",
            "instagram": "",
        }
    return {
        "name": salon.name,
        "description": salon.description,
        "address": salon.address,
        "phone": salon.phone,
        "working_hours_text": salon.working_hours_text,
        "instagram": salon.instagram,
    }


@router.patch("/salon")
async def update_salon(
    data: SalonUpdate,
    admin_id: int = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(select(SalonInfo).limit(1))
    salon = result.scalar_one_or_none()
    if not salon:
        salon = SalonInfo()
        db.add(salon)

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(salon, key, value)

    await db.commit()
    await db.refresh(salon)
    return {
        "name": salon.name,
        "description": salon.description,
        "address": salon.address,
        "phone": salon.phone,
        "working_hours_text": salon.working_hours_text,
        "instagram": salon.instagram,
    }


@router.get("/faq", response_model=list[FaqResponse])
async def get_faq(db: AsyncSession = Depends(get_db)) -> list[FaqResponse]:
    result = await db.execute(select(FaqItem).order_by(FaqItem.order_index))
    return result.scalars().all()


@router.post("/faq", response_model=FaqResponse, status_code=201)
async def create_faq(
    data: FaqCreate,
    admin_id: int = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> FaqResponse:
    item = FaqItem(**data.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/faq/{faq_id}", response_model=FaqResponse)
async def update_faq(
    faq_id: int,
    data: FaqUpdate,
    admin_id: int = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> FaqResponse:
    result = await db.execute(select(FaqItem).where(FaqItem.id == faq_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="FAQ item not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)

    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/faq/{faq_id}", status_code=204)
async def delete_faq(
    faq_id: int,
    admin_id: int = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(FaqItem).where(FaqItem.id == faq_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="FAQ item not found")

    await db.delete(item)
    await db.commit()


@router.put("/faq/reorder", response_model=list[FaqResponse])
async def reorder_faq(
    data: FaqReorder,
    admin_id: int = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[FaqResponse]:
    """Принимает список id в нужном порядке, обновляет order_index."""
    result = await db.execute(select(FaqItem).where(FaqItem.id.in_(data.ids)))
    items_map = {item.id: item for item in result.scalars().all()}

    if len(items_map) != len(data.ids):
        raise HTTPException(status_code=400, detail="Some FAQ ids not found")

    for idx, faq_id in enumerate(data.ids):
        items_map[faq_id].order_index = idx

    await db.commit()

    result = await db.execute(select(FaqItem).order_by(FaqItem.order_index))
    return result.scalars().all()
