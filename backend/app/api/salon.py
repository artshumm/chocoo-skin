from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import FaqItem, SalonInfo

router = APIRouter(prefix="/api", tags=["salon"])


@router.get("/salon")
async def get_salon_info(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SalonInfo).limit(1))
    salon = result.scalar_one_or_none()
    if not salon:
        return {
            "name": "Chocoo Skin",
            "description": "Салон загара",
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


@router.get("/faq")
async def get_faq(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FaqItem).order_by(FaqItem.order_index))
    items = result.scalars().all()
    return [
        {"id": item.id, "question": item.question, "answer": item.answer}
        for item in items
    ]
