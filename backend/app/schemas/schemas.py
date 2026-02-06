from datetime import date, datetime, time

from pydantic import BaseModel, Field


# ── Users ──


class UserResponse(BaseModel):
    id: int
    telegram_id: int
    username: str | None
    first_name: str | None
    phone: str | None
    consent_given: bool
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    """Клиент обновляет профиль."""

    first_name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., pattern=r"^\+375\d{9}$")
    consent_given: bool


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
    start_hour: int = Field(default=8, ge=0, le=23)
    start_minute: int = Field(default=30, ge=0, le=59)
    end_hour: int = Field(default=21, ge=1, le=23)
    end_minute: int = Field(default=0, ge=0, le=59)
    interval_minutes: int = Field(default=30, ge=10, le=120)


class SlotUpdate(BaseModel):
    """Админ блокирует/разблокирует слот."""

    status: str = Field(..., pattern=r"^(available|blocked)$")


# ── Bookings ──


class BookingCreate(BaseModel):
    """Клиент записывается. telegram_id извлекается из initData."""

    service_id: int = Field(..., gt=0)
    slot_id: int = Field(..., gt=0)
    remind_before_hours: int = Field(default=2, ge=1, le=24)


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

    name: str = Field(..., min_length=1, max_length=255)
    amount: float = Field(..., gt=0, le=999999.99)
    month: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$")


class ExpenseResponse(BaseModel):
    id: int
    name: str
    amount: float
    month: str
    created_at: datetime

    model_config = {"from_attributes": True}
