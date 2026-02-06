"""
Миграция: добавляем consent_given и consent_date в таблицу users.

Запуск:
    cd backend
    python migrate_consent.py
"""

import asyncio

from sqlalchemy import text

from app.core.database import async_session


MIGRATIONS = [
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS consent_given BOOLEAN DEFAULT false",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS consent_date TIMESTAMP",
]


async def migrate():
    async with async_session() as session:
        for sql in MIGRATIONS:
            print(f"  → {sql[:60]}...")
            await session.execute(text(sql))
        await session.commit()
        print("Миграция consent выполнена!")


if __name__ == "__main__":
    asyncio.run(migrate())
