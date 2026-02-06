# Chocoo Skin - Telegram Mini App для салона загара

## Проект
Telegram Mini App для записи клиентов в салон загара.
MVP для одного салона с возможностью масштабирования (добавление мастеров).

## Архитектура (DOE)
- **D (Directive)** - этот файл. Системный промпт. Читается перед каждым сообщением.
- **O (Orchestration)** - AI агент решает что и когда делать. Читает memory.md для контекста.
- **E (Execution)** - скрипты и инструменты выполняют конкретные действия.

## Правила разработки

1. **Before code** — Before writing any code, describe your approach and wait for approval. Always ask clarifying questions before writing any code if requirements are ambiguous.
2. **>3 files** — If a task requires changes to more than 3 files, stop and break it into smaller tasks first.
3. **After code** — After writing code, list what could break and suggest tests to cover it.
4. **Bug fix** — When there's a bug, start by writing a test that reproduces it, then fix it until the test passes.
5. **Self-correction** — Every time I correct you, add a new rule to the CLAUDE.md file so it never happens again.
6. **Memory** — всегда читать memory.md в начале сессии. **Автосохранение**: после каждого завершённого действия (фикс, фича, деплой, аудит) немедленно записывать результат в memory.md. Не ждать конца сессии — сохранять сразу.
7. **Credentials** — ВСЕ пароли, API ключи и токены (Telegram, Railway, Neon, любые другие) записывать ТОЛЬКО в `credentials.md`. Файл ОБЯЗАН быть в `.gitignore` — НИКОГДА не коммитить, не пушить, не показывать, не копировать содержимое. При получении нового ключа — СРАЗУ записать в credentials.md. При деплое — читать токены из credentials.md, не хардкодить в команды.
8. **Clarifying questions** — перед реализацией каждого шага задавать МИНИМУМ 5 уточняющих вопросов. Не начинать код пока не получены ответы.
9. **Security & Quality** — при каждом изменении кода проверять на уязвимости (OWASP Top 10, IDOR, race conditions, input validation), баги и edge cases. Постоянно совершенствовать приложение: оптимизировать запросы, закрывать дыры, улучшать UX. Читать audit-секцию в memory.md для контекста.

## Функции MVP

### Клиент:
- Информация о салоне + FAQ
- Выбор даты и времени записи (календарь на 2 недели)
- Мои записи + отмена
- Напоминания через Telegram

### Админ:
- Расписание на 2 недели вперед
- Закрытие/открытие слотов
- Просмотр записей
- Уведомления о новых записях

### НЕ в MVP:
- Онлайн-оплата
- Портфолио мастеров
- Каталог салонов

## Tech Stack

| Часть | Технология | Версия |
|-------|------------|--------|
| Frontend | React + TypeScript + Vite | React 18 |
| TMA SDK | @telegram-apps/sdk-react | latest |
| UI | TelegramUI | latest |
| Backend | Python + FastAPI | Python 3.11+ |
| ORM | SQLAlchemy + Alembic | 2.0 |
| Bot | aiogram | 3.x |
| БД | PostgreSQL | 16 |
| Контейнеры | Docker + Docker Compose | - |

## Структура проекта

```
Chocoo skin/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI + aiogram запуск
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   └── config.py        # Настройки из .env
│   │   ├── bot/
│   │   │   ├── __init__.py
│   │   │   └── handlers.py      # /start, админ-команды
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── models.py        # SQLAlchemy модели
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   └── schemas.py       # Pydantic схемы
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── slot_service.py
│   │   │   └── booking_service.py
│   │   └── api/
│   │       ├── __init__.py
│   │       ├── salon.py         # GET /api/salon, /api/faq
│   │       ├── slots.py         # GET /api/slots
│   │       └── bookings.py      # POST/GET /api/bookings
│   ├── alembic/
│   ├── requirements.txt
│   └── alembic.ini
│
├── frontend/                     # Mini App (React) - Шаг 3
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── api/
│   │   └── types/
│   ├── package.json
│   └── vite.config.ts
│
├── content/                      # Контент для клиентов
│   ├── faq_draft.txt             # Черновик FAQ (для редактирования)
│   └── faq_spray_tan.md          # Финальный FAQ (30 вопросов/ответов)
│
├── .env                          # Секреты (НЕ в git)
├── .env.example
├── .gitignore
├── docker-compose.yml
├── CLAUDE.md                     # D - Directive (этот файл)
└── memory.md                     # Журнал прогресса
```

## База данных (6 таблиц)

```
users          - telegram_id, username, first_name, phone, role
salon_info     - name, description, address, phone, working_hours_text
faq_items      - question, answer, order_index
services       - name, description, duration_minutes, price, is_active
slots          - date, start_time, end_time, status (available/booked/blocked)
bookings       - client_id, service_id, slot_id, status, created_at
```

## API эндпоинты

```
GET  /api/salon           - информация о салоне
GET  /api/faq             - список FAQ
GET  /api/services        - список услуг
GET  /api/slots?date=     - доступные слоты на дату
POST /api/bookings        - создать запись
GET  /api/bookings/my     - мои записи
DELETE /api/bookings/{id} - отменить запись
```

## Переменные окружения

```
BOT_TOKEN=           # токен из @BotFather
ADMIN_ID=            # telegram ID администратора
DATABASE_URL=        # postgresql://user:pass@host:5432/dbname
MINI_APP_URL=        # URL фронтенда (после деплоя на Vercel)
```

## Команды

```bash
# PostgreSQL
docker-compose up -d

# Backend
cd backend
pip install -r requirements.txt
python -m app.main

# Загрузить FAQ в БД
cd backend
python seed_faq.py

# Frontend (Шаг 3)
cd frontend
npm install
npm run dev
```

## Текущий этап
Шаг 3: Frontend Mini App (React + Telegram Mini App SDK)
