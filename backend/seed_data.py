"""
Seed-скрипт для загрузки услуг и информации о салоне в базу данных.

=== ИНСТРУКЦИЯ ДЛЯ НОВОГО КЛИЕНТА ===
1. Замените SALON_DATA на данные нового салона (название, адрес, телефон, Instagram)
2. Замените SERVICES_DATA на услуги нового салона (название, описание, длительность, цена)
3. Замените PREPARATION_TEXT на рекомендации по подготовке к услуге (или оставьте пустым)
4. Запустите: cd backend && python seed_data.py

Запуск:
    cd backend
    python seed_data.py

Скрипт:
1. Выполняет ALTER TABLE (добавляет новые колонки если их нет)
2. Удаляет все существующие услуги и данные салона
3. Вставляет услуги + информацию о салоне
"""

import asyncio

from sqlalchemy import delete, text

from app.core.database import async_session
from app.models.models import SalonInfo, Service

# ============================================================
# ДАННЫЕ САЛОНА — замените на данные вашего клиента
# ============================================================

SALON_DATA = {
    "name": "Название салона",              # Название бизнеса
    "description": "Описание салона",        # Краткое описание
    "address": "г. Город, ул. Улица, д. 1", # Адрес
    "phone": "+375XXXXXXXXX",               # Телефон (международный формат)
    "working_hours_text": "",                # Часы работы (необязательно)
    "instagram": "",                         # Ссылка на Instagram (необязательно)
    "preparation_text": "",                  # Рекомендации по подготовке (необязательно)
}

# ============================================================
# УСЛУГИ — замените на услуги вашего клиента
# ============================================================

SERVICES_DATA = [
    {
        "name": "Услуга 1",                 # Название услуги
        "short_description": "Краткое описание",  # Отображается в списке
        "description": "Полное описание услуги",   # Детальное описание
        "duration_minutes": 30,              # Длительность в минутах
        "price": 50.00,                      # Цена в BYN
        "is_active": True,                   # True = видна клиентам
    },
    # Добавьте больше услуг по образцу выше
]


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
