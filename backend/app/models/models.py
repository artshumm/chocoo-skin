import enum
from datetime import date, datetime, time

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    client = "client"
    admin = "admin"


class SlotStatus(str, enum.Enum):
    available = "available"
    booked = "booked"
    blocked = "blocked"


class BookingStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    completed = "completed"
    cancelled = "cancelled"


# ── 1. Пользователи ──


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.client)
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    bookings: Mapped[list["Booking"]] = relationship(back_populates="client")


# ── 2. Информация о салоне ──


class SalonInfo(Base):
    __tablename__ = "salon_info"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), default="Chocoo Skin")
    description: Mapped[str] = mapped_column(Text, default="")
    address: Mapped[str] = mapped_column(String(500), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    working_hours_text: Mapped[str] = mapped_column(String(500), default="")
    instagram: Mapped[str] = mapped_column(String(500), default="")


# ── 3. FAQ ──


class FaqItem(Base):
    __tablename__ = "faq_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer, default=0)


# ── 4. Услуги ──


class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    short_description: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    bookings: Mapped[list["Booking"]] = relationship(back_populates="service")


# ── 5. Слоты записи ──


class Slot(Base):
    __tablename__ = "slots"
    __table_args__ = (
        Index("ix_slot_date_status", "date", "status"),
        UniqueConstraint("date", "start_time", "end_time", name="uq_slot_datetime"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    status: Mapped[SlotStatus] = mapped_column(
        Enum(SlotStatus), default=SlotStatus.available
    )

    booking: Mapped["Booking | None"] = relationship(back_populates="slot")


# ── 6. Записи ──


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        Index("ix_booking_status_reminded", "status", "reminded"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))
    slot_id: Mapped[int] = mapped_column(ForeignKey("slots.id"), unique=True)
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus), default=BookingStatus.confirmed, index=True
    )
    remind_before_hours: Mapped[int] = mapped_column(Integer, server_default="2")
    reminded: Mapped[bool] = mapped_column(Boolean, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    client: Mapped["User"] = relationship(back_populates="bookings")
    service: Mapped["Service"] = relationship(back_populates="bookings")
    slot: Mapped["Slot"] = relationship(back_populates="booking")


# ── 7. Расходы ──


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    month: Mapped[str] = mapped_column(String(7), index=True)  # "2026-02"
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
