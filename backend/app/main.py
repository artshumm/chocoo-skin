import asyncio
import logging

from aiogram import Dispatcher
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api.bookings import router as bookings_router
from app.api.expenses import router as expenses_router
from app.api.salon import router as salon_router
from app.api.services import router as services_router
from app.api.slots import router as slots_router
from app.api.users import router as users_router
from app.bot.bot_instance import bot
from app.bot.handlers import router as bot_router
from app.bot.scheduler import run_scheduler
from app.core.config import settings
from app.core.database import engine
from app.models.models import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dp = Dispatcher()
dp.include_router(bot_router)


async def start_bot() -> None:
    logger.info("Starting Telegram bot...")
    await dp.start_polling(bot)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables + start bot polling
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")

    bot_task = asyncio.create_task(start_bot())
    scheduler_task = asyncio.create_task(run_scheduler())
    yield

    # Shutdown
    scheduler_task.cancel()
    bot_task.cancel()
    await bot.session.close()
    await engine.dispose()


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
app.include_router(salon_router)
app.include_router(users_router)
app.include_router(services_router)
app.include_router(slots_router)
app.include_router(bookings_router)
app.include_router(expenses_router)


@app.get("/")
async def root():
    return {"status": "ok", "project": "Chocoo Skin"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
