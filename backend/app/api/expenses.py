from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.models import Expense
from app.schemas.schemas import ExpenseCreate, ExpenseResponse

router = APIRouter(prefix="/api/expenses", tags=["expenses"])


@router.get("/", response_model=list[ExpenseResponse])
async def get_expenses(
    month: str = Query(..., description="Месяц в формате YYYY-MM", pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    _admin: int = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[ExpenseResponse]:
    """Расходы за указанный месяц — для админа."""
    result = await db.execute(
        select(Expense)
        .where(Expense.month == month)
        .order_by(Expense.created_at.desc())
    )
    return result.scalars().all()


@router.post("/", response_model=ExpenseResponse)
async def create_expense(
    data: ExpenseCreate,
    _admin: int = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ExpenseResponse:
    """Админ добавляет расход."""
    expense = Expense(name=data.name, amount=data.amount, month=data.month)
    db.add(expense)
    await db.commit()
    await db.refresh(expense)
    return expense


@router.delete("/{expense_id}")
async def delete_expense(
    expense_id: int,
    _admin: int = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Админ удаляет расход."""
    expense = await db.get(Expense, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Расход не найден")
    await db.delete(expense)
    await db.commit()
    return {"ok": True}
