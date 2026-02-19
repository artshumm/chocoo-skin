from datetime import date, datetime, time

from pydantic import BaseModel, Field, model_validator


# ── Users ──


class UserResponse(BaseModel):
    id: int
    telegram_id: int
    username: str | None
    first_name: str | None
    phone: str | None
    instagram: str | None = None
    consent_given: bool
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    """Клиент обновляет профиль."""

    first_name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., pattern=r"^\+\d{7,15}$")
    instagram: str | None = Field(None, max_length=31, pattern=r"^@[A-Za-z0-9_.]+$")
    consent_given: bool


# ── Salon ──


class SalonUpdate(BaseModel):
    """Админ обновляет информацию о салоне."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    address: str | None = Field(None, max_length=500)
    phone: str | None = Field(None, max_length=20)
    working_hours_text: str | None = Field(None, max_length=500)
    instagram: str | None = Field(None, max_length=500)
    preparation_text: str | None = Field(None, max_length=5000)


# ── Services ──


class ServiceCreate(BaseModel):
    """Админ создаёт услугу."""

    name: str = Field(..., min_length=1, max_length=255)
    short_description: str = Field(default="", max_length=500)
    description: str = Field(default="", max_length=2000)
    duration_minutes: int = Field(default=20, ge=10, le=480)
    price: float = Field(..., gt=0, le=999999.99)
    is_active: bool = True


class ServiceUpdate(BaseModel):
    """Админ обновляет услугу (partial)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    short_description: str | None = Field(None, max_length=500)
    description: str | None = Field(None, max_length=2000)
    duration_minutes: int | None = Field(None, ge=10, le=480)
    price: float | None = Field(None, gt=0, le=999999.99)
    is_active: bool | None = None


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
    interval_minutes: int = Field(default=20, ge=10, le=120)

    @model_validator(mode="after")
    def validate_time_range(self):
        start = self.start_hour * 60 + self.start_minute
        end = self.end_hour * 60 + self.end_minute
        if start >= end:
            raise ValueError("start_time must be before end_time")
        return self


class SlotUpdate(BaseModel):
    """Админ блокирует/разблокирует слот."""

    status: str = Field(..., pattern=r"^(available|blocked)$")


# ── Bookings ──


class BookingCreate(BaseModel):
    """Клиент записывается. telegram_id извлекается из initData."""

    service_id: int = Field(..., gt=0)
    slot_id: int = Field(..., gt=0)
    remind_before_hours: int = Field(default=2, ge=1, le=24)


class BookingReschedule(BaseModel):
    """Админ переносит запись на другой слот."""

    new_slot_id: int = Field(..., gt=0)


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


# ── FAQ ──


class FaqResponse(BaseModel):
    id: int
    question: str
    answer: str
    order_index: int

    model_config = {"from_attributes": True}


class FaqCreate(BaseModel):
    """Админ добавляет FAQ."""

    question: str = Field(..., min_length=1, max_length=500)
    answer: str = Field(..., min_length=1, max_length=2000)
    order_index: int = Field(default=0, ge=0)


class FaqUpdate(BaseModel):
    """Админ обновляет FAQ (partial)."""

    question: str | None = Field(None, min_length=1, max_length=500)
    answer: str | None = Field(None, min_length=1, max_length=2000)
    order_index: int | None = Field(None, ge=0)


class FaqReorder(BaseModel):
    """Массовое изменение порядка FAQ."""

    ids: list[int] = Field(..., min_length=1, max_length=100)


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


# ── Schedule Templates ──

DAY_NAMES = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]


class ScheduleTemplateItem(BaseModel):
    """One day template."""

    day_of_week: int = Field(..., ge=0, le=6, description="0=Пн..6=Вс")
    start_time: time
    end_time: time
    interval_minutes: int = Field(default=20, ge=10, le=120)
    is_active: bool = True

    @model_validator(mode="after")
    def validate_times(self):
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")
        return self


class ScheduleTemplateResponse(ScheduleTemplateItem):
    id: int

    model_config = {"from_attributes": True}


class ScheduleTemplateBulk(BaseModel):
    """Bulk upsert of schedule templates."""

    templates: list[ScheduleTemplateItem] = Field(..., max_length=7)
