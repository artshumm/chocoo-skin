from datetime import date, datetime, time

from pydantic import BaseModel


# ── Users ──


class UserAuth(BaseModel):
    """Данные из Telegram для регистрации/логина."""

    telegram_id: int
    username: str | None = None
    first_name: str | None = None


class UserResponse(BaseModel):
    id: int
    telegram_id: int
    username: str | None
    first_name: str | None
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Services ──


class ServiceResponse(BaseModel):
    id: int
    name: str
    short_description: str
    description: str
    duration_minutes: int
    price: float
    is_active: bool

    model_config = {"from_attributes": True}


# ── Slots ──


class SlotResponse(BaseModel):
    id: int
    date: date
    start_time: time
    end_time: time
    status: str

    model_config = {"from_attributes": True}


class SlotCreate(BaseModel):
    """Админ создаёт слоты на день."""

    date: date
    start_hour: int = 9
    end_hour: int = 21
    interval_minutes: int = 30


class SlotUpdate(BaseModel):
    """Админ блокирует/разблокирует слот."""

    status: str  # "available" | "blocked"


# ── Bookings ──


class BookingCreate(BaseModel):
    """Клиент записывается."""

    telegram_id: int
    service_id: int
    slot_id: int
    remind_before_hours: int = 2


class BookingResponse(BaseModel):
    id: int
    status: str
    remind_before_hours: int
    reminded: bool
    created_at: datetime
    client: UserResponse
    service: ServiceResponse
    slot: SlotResponse

    model_config = {"from_attributes": True}


# ── Expenses ──


class ExpenseCreate(BaseModel):
    """Админ добавляет расход."""

    name: str
    amount: float
    month: str  # "YYYY-MM"


class ExpenseResponse(BaseModel):
    id: int
    name: str
    amount: float
    month: str
    created_at: datetime

    model_config = {"from_attributes": True}
