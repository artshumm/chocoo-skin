import asyncio
import logging

from aiogram import Dispatcher
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.bookings import router as bookings_router
from app.api.expenses import router as expenses_router
from app.api.salon import router as salon_router
from app.api.schedule_templates import router as schedule_templates_router
from app.api.services import router as services_router
from app.api.slots import router as slots_router
from app.api.users import router as users_router
from app.bot.bot_instance import bot
from app.bot.handlers import router as bot_router
from app.bot.scheduler import run_scheduler
from app.core.config import settings
from app.core.database import engine, get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dp = Dispatcher()
dp.include_router(bot_router)


async def start_bot() -> None:
    logger.info("Starting Telegram bot...")
    await dp.start_polling(bot)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: start bot polling + scheduler
    # DB schema managed by Alembic (alembic upgrade head)
    bot_task = asyncio.create_task(start_bot())
    scheduler_task = asyncio.create_task(run_scheduler())
    yield

    # Graceful shutdown: ждём завершения задач
    scheduler_task.cancel()
    bot_task.cancel()
    await asyncio.gather(scheduler_task, bot_task, return_exceptions=True)
    await bot.session.close()
    await engine.dispose()
    logger.info("Shutdown complete")


app = FastAPI(title="Chocoo Skin API", lifespan=lifespan)

# CORS: разрешаем только фронтенд из MINI_APP_URL + localhost для разработки
_cors_origins: list[str] = []
if settings.mini_app_url:
    _cors_origins.append(settings.mini_app_url.rstrip("/"))
if settings.skip_telegram_validation:
    _cors_origins.extend(["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(GZipMiddleware, minimum_size=500)
app.include_router(salon_router)
app.include_router(users_router)
app.include_router(services_router)
app.include_router(slots_router)
app.include_router(bookings_router)
app.include_router(expenses_router)
app.include_router(schedule_templates_router)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(status_code=500, content={"detail": "Внутренняя ошибка сервера"})


@app.get("/")
async def root():
    return {"status": "ok", "project": "Chocoo Skin"}


@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "error", "db": "disconnected"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
