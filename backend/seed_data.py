"""
Seed-скрипт для загрузки услуг и информации о салоне в базу данных.

Запуск:
    cd backend
    python seed_data.py

Скрипт:
1. Выполняет ALTER TABLE (добавляет новые колонки если их нет)
2. Удаляет все существующие услуги и данные салона
3. Вставляет 4 услуги + 1 запись salon_info
"""

import asyncio

from sqlalchemy import delete, text

from app.core.database import async_session
from app.models.models import SalonInfo, Service

FULL_DESCRIPTION = (
    "Загар лосьонами premium. На ваш выбор оттенок и интенсивность загара. "
    "Барьерный крем на руки, стопы, ногти. "
    "Индивидуальный набор: шапочка, трусики-бикини, тапочки, стикини, резинка для волос. "
    "Нанесение профессиональным оборудованием лосьона на все тело и лицо. "
    "Пилинг на проблемные зоны (подмышки, голени). "
    "Финиш-пудра для комфорта на проблемные участки."
)

SERVICES_DATA = [
    {
        "name": "Загар (Classic)",
        "short_description": "Моментальный загар всего тела, лосьоны premium",
        "description": FULL_DESCRIPTION,
        "duration_minutes": 20,
        "price": 55.00,
        "is_active": True,
    },
    {
        "name": "Детский загар (до 10 лет)",
        "short_description": "Моментальный загар для детей до 10 лет",
        "description": FULL_DESCRIPTION,
        "duration_minutes": 20,
        "price": 30.00,
        "is_active": True,
    },
    {
        "name": "Детский загар (до 14 лет)",
        "short_description": "Моментальный загар для детей до 14 лет",
        "description": FULL_DESCRIPTION,
        "duration_minutes": 20,
        "price": 35.00,
        "is_active": True,
    },
    {
        "name": "Детский загар: только ноги",
        "short_description": "Моментальный загар ног для детей",
        "description": "Нанесение лосьона только на ноги.",
        "duration_minutes": 15,
        "price": 20.00,
        "is_active": True,
    },
]

SALON_DATA = {
    "name": "Chocoo Skin",
    "description": "Салон моментального загара. Работаем только по предварительной записи",
    "address": "г. Гродно, ТЦ Юлан (возле Геммы), ул. Космонавтов 2/1, 2 этаж",
    "phone": "+375 (29) 749-22-95",
    "working_hours_text": "Пн-Пт: 8:30-21:00, Сб: 8:30-16:00, Вс: выходной",
    "instagram": "https://www.instagram.com/chocoo.skin/",
}


async def seed():
    async with async_session() as session:
        # ALTER TABLE: добавляем новые колонки если их нет
        await session.execute(
            text(
                "ALTER TABLE services "
                "ADD COLUMN IF NOT EXISTS short_description TEXT DEFAULT ''"
            )
        )
        await session.execute(
            text(
                "ALTER TABLE salon_info "
                "ADD COLUMN IF NOT EXISTS instagram VARCHAR(500) DEFAULT ''"
            )
        )
        await session.commit()
        print("ALTER TABLE выполнен")

    async with async_session() as session:
        # Удаляем старые данные
        await session.execute(delete(Service))
        await session.execute(delete(SalonInfo))
        await session.flush()

        # Вставляем услуги
        for item in SERVICES_DATA:
            service = Service(**item)
            session.add(service)

        # Вставляем информацию о салоне
        salon = SalonInfo(**SALON_DATA)
        session.add(salon)

        await session.commit()
        print(f"Загружено: {len(SERVICES_DATA)} услуг + информация о салоне")


if __name__ == "__main__":
    asyncio.run(seed())
