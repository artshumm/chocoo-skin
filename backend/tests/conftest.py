"""Test fixtures: SQLite in-memory DB, auth overrides, seed data."""

from datetime import date, time
from unittest.mock import AsyncMock, patch

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_telegram_user, require_admin
from app.core.database import get_db
from app.models.models import (
    Base,
    Expense,
    FaqItem,
    SalonInfo,
    Service,
    Slot,
    SlotStatus,
    User,
)

# --- SQLite FOR UPDATE workaround ---
# SQLite doesn't support SELECT ... FOR UPDATE.
# Monkey-patch the compiler to make it a no-op.
from sqlalchemy.dialects.sqlite.base import SQLiteCompiler

SQLiteCompiler._generate_for_update_clause = lambda self, arg: ""

# --- Test DB (SQLite in-memory, single connection via StaticPool) ---
engine_test = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = async_sessionmaker(engine_test, class_=AsyncSession, expire_on_commit=False)

# --- Test identities ---
TEST_USER = {"id": 12345, "username": "testuser", "first_name": "Test"}
TEST_ADMIN_ID = 446746688
TEST_ADMIN = {"id": TEST_ADMIN_ID, "username": "admin", "first_name": "Admin"}


# --- DB setup / teardown (autouse) ---
@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _override_get_db():
    async with TestSession() as session:
        yield session


# --- HTTP clients ---
@pytest_asyncio.fixture
async def client():
    """Regular user client (telegram_id=12345)."""
    from app.main import app

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_telegram_user] = lambda: TEST_USER
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_client():
    """Admin client (telegram_id=446746688)."""
    from app.main import app

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_telegram_user] = lambda: TEST_ADMIN
    app.dependency_overrides[require_admin] = lambda: TEST_ADMIN_ID
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# --- Raw DB session ---
@pytest_asyncio.fixture
async def db():
    async with TestSession() as session:
        yield session


# --- Seed data ---
@pytest_asyncio.fixture
async def seed_user(db):
    user = User(
        telegram_id=TEST_USER["id"],
        username="testuser",
        first_name="Test",
        consent_given=True,
        phone="+375291234567",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def seed_service(db):
    svc = Service(
        name="Автозагар",
        short_description="Спрей-загар",
        description="Профессиональный spray tan",
        duration_minutes=20,
        price=50.00,
        is_active=True,
    )
    db.add(svc)
    await db.commit()
    await db.refresh(svc)
    return svc


@pytest_asyncio.fixture
async def seed_slot(db):
    """Slot far in the future (2026-12-25 10:00-10:20)."""
    slot = Slot(
        date=date(2026, 12, 25),
        start_time=time(10, 0),
        end_time=time(10, 20),
        status=SlotStatus.available,
    )
    db.add(slot)
    await db.commit()
    await db.refresh(slot)
    return slot


@pytest_asyncio.fixture
async def seed_salon(db):
    salon = SalonInfo(
        name="Test Salon",
        description="Салон загара",
        address="ул. Тестовая, 1",
        phone="+375291234567",
        working_hours_text="9:00-21:00",
        instagram="@testsalon",
    )
    db.add(salon)
    await db.commit()
    await db.refresh(salon)
    return salon


@pytest_asyncio.fixture
async def seed_faq(db):
    items = [
        FaqItem(question="Что это?", answer="Салон загара", order_index=0),
        FaqItem(question="Цена?", answer="От 50 BYN", order_index=1),
    ]
    db.add_all(items)
    await db.commit()
    return items


@pytest_asyncio.fixture
def mock_notifications():
    """Mock all bot notification functions."""
    with (
        patch("app.api.bookings.notify_admins_new_booking", new_callable=AsyncMock) as m1,
        patch("app.api.bookings.notify_client_booking_confirmed", new_callable=AsyncMock) as m2,
        patch("app.api.bookings.notify_admins_cancelled_booking", new_callable=AsyncMock) as m3,
        patch("app.api.bookings.notify_client_booking_cancelled_by_admin", new_callable=AsyncMock) as m4,
    ):
        yield {"new": m1, "confirmed": m2, "cancelled": m3, "admin_cancelled": m4}
