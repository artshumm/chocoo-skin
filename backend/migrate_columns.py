"""
Миграция: добавляем недостающие колонки во все таблицы.

Запуск:
    cd backend
    python migrate_columns.py

create_all НЕ обновляет существующие таблицы — нужен ALTER TABLE.
"""

import asyncio

from sqlalchemy import text

from app.core.database import async_session


MIGRATIONS = [
    # bookings: remind_before_hours, reminded
    "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS remind_before_hours INTEGER DEFAULT 2",
    "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS reminded BOOLEAN DEFAULT false",
    # services: short_description (уже было, на всякий случай)
    "ALTER TABLE services ADD COLUMN IF NOT EXISTS short_description TEXT DEFAULT ''",
    # salon_info: instagram (уже было, на всякий случай)
    "ALTER TABLE salon_info ADD COLUMN IF NOT EXISTS instagram VARCHAR(500) DEFAULT ''",
]


async def migrate():
    async with async_session() as session:
        for sql in MIGRATIONS:
            print(f"  → {sql[:60]}...")
            await session.execute(text(sql))
        await session.commit()
        print("Все миграции выполнены!")


if __name__ == "__main__":
    asyncio.run(migrate())
