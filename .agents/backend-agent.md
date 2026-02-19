# Backend Agent — Chocoo Skin

## Role
Expert backend developer for FastAPI + SQLAlchemy + PostgreSQL async applications.

## Tech Stack
- **Runtime:** Python 3.11+, FastAPI, Uvicorn
- **ORM:** SQLAlchemy 2.0 async (asyncpg)
- **DB:** PostgreSQL 16 (Neon), Alembic migrations
- **Bot:** aiogram 3.x (Telegram notifications)
- **Auth:** HMAC-SHA256 initData validation
- **Deploy:** Railway

## Skills (read before every task)
1. `.agents/skills/fastapi-pro/SKILL.md` — FastAPI patterns, async endpoints, dependency injection, Pydantic V2
2. `.agents/skills/python-pro/SKILL.md` — Modern Python, type hints, testing, performance
3. `.agents/skills/postgres-best-practices/SKILL.md` — Query optimization, indexes, connection pooling

## Project Structure
```
backend/
  app/
    main.py          — FastAPI app, middleware, lifespan
    core/
      config.py      — Pydantic Settings (env vars)
      database.py    — Async engine + session
      scheduler.py   — Asyncio scheduler (reminders, auto-complete, slot generation)
    bot/
      bot.py         — aiogram Bot instance
      handlers.py    — /start, /help commands
      notifications.py — Admin/client notifications
    models/
      models.py      — SQLAlchemy models (User, Slot, Booking, Service, SalonInfo, FAQ, ScheduleTemplate)
    schemas/
      schemas.py     — Pydantic schemas (validation, serialization)
    services/
      booking_service.py — Business logic
    api/
      deps.py        — get_telegram_user(), require_admin
      bookings.py    — CRUD bookings
      slots.py       — CRUD slots
      users.py       — Profile endpoints
      services.py    — Services CRUD
      salon.py       — Salon info + FAQ
      schedule_templates.py — Schedule templates
      expenses.py    — Expense tracking
  tests/             — pytest + httpx + aiosqlite (77 tests)
  alembic/           — DB migrations
```

## Key Patterns
- **Auth:** `Depends(get_telegram_user)` on every endpoint. Admin: `Depends(require_admin)`
- **DB locking:** `with_for_update()` on slot during booking/cancel (race condition prevention)
- **Timezone:** `MINSK_TZ = timezone(timedelta(hours=3))` — all datetime ops use this
- **Notifications:** Always wrap in try-catch, never block booking operations
- **Tests:** SQLite in-memory + aiosqlite, mock notifications with AsyncMock
- **Migrations:** `cd backend && .venv/bin/alembic revision --autogenerate -m "msg"`

## Rules
1. Always use async/await for DB operations
2. Validate all inputs with Pydantic schemas (regex, gt/ge/le constraints)
3. Use `with_for_update()` for any status-changing DB operations
4. Never expose stack traces — global exception handler returns sanitized JSON
5. Rate limiting: SlowAPI 100 req/min per IP
6. Security headers: CSP, HSTS, X-Frame-Options DENY, X-Content-Type-Options nosniff
7. Run `cd backend && .venv/bin/python -m pytest tests/ -q` after changes
8. Alembic for ALL schema changes (never use create_all in production)
