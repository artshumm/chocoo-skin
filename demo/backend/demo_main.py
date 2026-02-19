"""Demo backend — Chocoo Skin без Telegram бота, с SQLite и переключением ролей.

Запуск:
    cd <project_root>
    PYTHONPATH=. python -m demo.backend.demo_main

Или:
    cd <project_root>
    uvicorn demo.backend.demo_main:app --host 0.0.0.0 --port 8001 --reload
"""

import json
import logging
import os
import sys

# ---------------------------------------------------------------------------
# CRITICAL: Set env vars BEFORE any import from app.* —
# config.py instantiates Settings() at module level, which requires
# BOT_TOKEN and DATABASE_URL. bot_instance.py creates Bot(token=...)
# on import. We provide dummy values so the import chain doesn't crash.
# ---------------------------------------------------------------------------
os.environ.setdefault("BOT_TOKEN", "0000000000:AAFakeTokenForDemoMode_NotUsed")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://demo:demo@localhost/demo_unused")
os.environ.setdefault("SKIP_TELEGRAM_VALIDATION", "true")
os.environ.setdefault("ADMIN_IDS", "1000002")
os.environ.setdefault("SALON_NAME", "Chocoo Demo")
os.environ.setdefault("MINI_APP_URL", "")

# Add project root and backend/ to Python path so both
# `from app.*` and `from demo.*` imports work.
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_BACKEND_DIR = os.path.join(_PROJECT_ROOT, "backend")
for _p in (_PROJECT_ROOT, _BACKEND_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ---------------------------------------------------------------------------
# Now safe to import from app.*
# ---------------------------------------------------------------------------
from contextlib import asynccontextmanager
from urllib.parse import parse_qs

from fastapi import FastAPI, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette.middleware.gzip import GZipMiddleware

from app.api.bookings import router as bookings_router
from app.api.deps import get_telegram_user, require_admin
from app.api.expenses import router as expenses_router
from app.api.salon import router as salon_router
from app.api.schedule_templates import router as schedule_templates_router
from app.api.services import router as services_router
from app.api.slots import router as slots_router
from app.api.users import router as users_router
from app.core.database import get_db
from app.models.models import Base

from demo.backend.demo_reset import router as demo_router

# ---------------------------------------------------------------------------
# SQLite setup (same proven pattern as backend/tests/conftest.py)
# ---------------------------------------------------------------------------
from sqlalchemy.dialects.sqlite.base import SQLiteCompiler

SQLiteCompiler._generate_for_update_clause = lambda self, arg: ""  # noqa: E731

DEMO_DB_PATH = os.getenv("DEMO_DB_PATH", "demo.db")
DEMO_DB_URL = f"sqlite+aiosqlite:///{DEMO_DB_PATH}"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

demo_engine = create_async_engine(
    DEMO_DB_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)
DemoSession = async_sessionmaker(
    demo_engine, class_=AsyncSession, expire_on_commit=False
)


async def demo_get_db():
    """Yield SQLite session instead of production Neon/PostgreSQL."""
    async with DemoSession() as session:
        yield session


# ---------------------------------------------------------------------------
# Auth override: parse user from fake initData (no HMAC validation)
# ---------------------------------------------------------------------------
DEMO_CLIENT: dict[str, object] = {
    "id": 1000001,
    "username": "demo_client",
    "first_name": "Клиент",
}
DEMO_ADMIN: dict[str, object] = {
    "id": 1000002,
    "username": "demo_admin",
    "first_name": "Админ",
}


async def demo_get_telegram_user(authorization: str = Header("")) -> dict:
    """Parse user from initData query string without HMAC validation.

    Frontend sends: Authorization: tma user=<json>&...
    We extract user JSON and return dict with id, username, first_name.
    Falls back to DEMO_CLIENT if parsing fails.
    """
    if not authorization.startswith("tma "):
        return DEMO_CLIENT

    init_data = authorization[4:]
    try:
        parsed = parse_qs(init_data)
        user_json = parsed.get("user", [""])[0]
        if user_json:
            user = json.loads(user_json)
            return {
                "id": user.get("id", 1000001),
                "username": user.get("username", "demo"),
                "first_name": user.get("first_name", "Demo"),
            }
    except Exception:
        logger.debug("Failed to parse demo initData, falling back to DEMO_CLIENT")

    return DEMO_CLIENT


# ---------------------------------------------------------------------------
# Lifespan: create tables on startup
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all tables in SQLite on startup, dispose engine on shutdown."""
    async with demo_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Demo DB ready: %s", DEMO_DB_URL)
    yield
    await demo_engine.dispose()
    logger.info("Demo shutdown complete")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="Chocoo Skin Demo", lifespan=lifespan)

# Dependency overrides — redirect DB and auth to demo versions
app.dependency_overrides[get_db] = demo_get_db
app.dependency_overrides[get_telegram_user] = demo_get_telegram_user
# NOTE: require_admin is NOT overridden directly. It uses Depends(get_telegram_user)
# internally, so it picks up our demo_get_telegram_user automatically.
# ADMIN_IDS=1000002 is set in env above, so settings.admin_id_list includes
# the demo admin user.

# CORS for demo frontend (local dev + optional deployed URL)
DEMO_FRONTEND_URL = os.getenv("DEMO_FRONTEND_URL", "")
_cors_origins: list[str] = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
]
if DEMO_FRONTEND_URL:
    _cors_origins.append(DEMO_FRONTEND_URL.rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=500)

# Include ALL existing routers (reuse production API)
app.include_router(salon_router)
app.include_router(users_router)
app.include_router(services_router)
app.include_router(slots_router)
app.include_router(bookings_router)
app.include_router(expenses_router)
app.include_router(schedule_templates_router)

# Demo-specific router (reset endpoint)
app.include_router(demo_router)


# ---------------------------------------------------------------------------
# Demo-specific endpoints
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    return {"status": "ok", "mode": "demo"}


@app.get("/health")
async def health():
    return {"status": "ok", "db": "sqlite"}


@app.get("/api/demo/presets")
async def list_presets():
    """Список доступных пресетов для UI."""
    from demo.backend.presets import PRESETS

    result = []
    for key, preset in PRESETS.items():
        result.append(
            {
                "id": key,
                "name": preset["salon_data"]["name"],
                "description": preset["salon_data"]["description"],
            }
        )
    return result


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Demo error: %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Ошибка демо-сервера"},
    )


# ---------------------------------------------------------------------------
# Run with: python -m demo.backend.demo_main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "demo.backend.demo_main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
    )
