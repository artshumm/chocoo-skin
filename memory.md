# Memory - Журнал прогресса Chocoo Skin

---

## ТЕКУЩИЙ СТАТУС
**Дата:** 2026-02-06
**Этап:** Шаг 5 ЗАВЕРШЁН. Все 5 шагов выполнены. Готовы к деплою.
**Бот:** @chocooskinbot - уведомления админам + клиентам, напоминания, утренняя сводка
**БД:** Neon PostgreSQL 17.7 - подключена, 7 таблиц

---

## ХРОНОЛОГИЯ

### День 1 (2026-02-05)
- [x] Создана директория проекта
- [x] Исследование: сравнение 4 вариантов (бот, Mini App, мобильное, PWA)
- [x] Изучены конкуренты: YCLIENTS, Dikidi, Booksy
- [x] Выбрано: Telegram Mini App
- [x] Уточнены требования: 1 салон, без оплаты, 30мин сеансы
- [x] Созданы CLAUDE.md и memory.md
- [x] Составлен план (5 шагов)

### День 2 (2026-02-06)
- [x] Получен токен бота через @BotFather
- [x] Принята DOE архитектура (Directive-Orchestration-Execution)
- [x] CLAUDE.md перезаписан как системный промпт
- [x] Шаг 1.1: .env, .env.example, .gitignore, docker-compose.yml, requirements.txt, config.py
- [x] Шаг 1.2: models.py (6 таблиц - User, SalonInfo, FaqItem, Service, Slot, Booking)
- [x] Шаг 1.3: handlers.py (/start), salon.py (API), database.py, main.py (FastAPI + aiogram)
- [x] Supabase — не работает (IPv6 only, pooler не находит проект). Удалён
- [x] Neon.tech — подключен, все 6 таблиц созданы
- [x] Бот @chocooskinbot — протестирован, работает
- [x] Шаг 2.1: schemas.py (Pydantic модели для request/response)
- [x] Шаг 2.2: deps.py (проверка админа), users.py (auth), services.py (список услуг)
- [x] Шаг 2.3: slots.py (получение/генерация/блокировка слотов)
- [x] Шаг 2.4: bookings.py (запись/мои записи/отмена/все записи для админа)
- [x] Шаг 2.5: main.py обновлён, все 11 эндпоинтов работают
- [x] Полный flow протестирован: регистрация → услуги → слоты → запись → отмена
- [x] Шаг 3.1-3.2: Vite + React + TS, API client, types, useTelegram hook
- [x] Шаг 3.3: CORS middleware, стили (Telegram-нативные), NavBar, App.tsx, main.tsx
- [x] Шаг 3.4: Calendar (14 дней) + TimeGrid (chips)
- [x] Шаг 3.5: BookingPage (услуга → дата → время → запись)
- [x] Шаг 3.6: MyBookingsPage (список + отмена)
- [x] Шаг 3.7: AdminPage (управление слотами + просмотр записей)
- [x] Шаг 3.8: npm run build — OK, 0 TS ошибок
- [x] Шаг 3.9: Calendar обновлён — полный месяц, 14 дней кликабельны, навигация по месяцам
- [x] Шаг 3.10: StatsPage — статистика доходов (сегодня/неделя/месяц) + расходы (CRUD в БД) + чистая прибыль
- [x] Шаг 3.10.1: Модель Expense в models.py, схемы в schemas.py
- [x] Шаг 3.10.2: API expenses.py (GET/POST/DELETE), подключен в main.py
- [x] Шаг 3.10.3: StatsPage.tsx, роут /stats, 5-я вкладка NavBar "Стат.", CSS-стили
- [x] Шаг 3.10.4: npm run build — OK, 0 TS ошибок
- [x] Поддержка 2 админов: ADMIN_IDS в .env, config.py, deps.py, users.py
- [x] Шаг 4.1: bot_instance.py — Bot вынесен в отдельный модуль
- [x] Шаг 4.2: notifications.py — уведомления админам (новая запись / отмена)
- [x] Шаг 4.3: bookings.py — вызов уведомлений после create/cancel
- [x] Шаг 4.4: main.py — импорт bot из bot_instance
- [x] Шаг 5.1: +remind_before_hours, +reminded в Booking (model + schema)
- [x] Шаг 5.2: notify_client_booking_confirmed() + вызов в bookings.py
- [x] Шаг 5.3: scheduler.py — напоминания клиентам + утренняя сводка админам (8:00 Минск)
- [x] Шаг 5.4: scheduler_task в main.py lifespan
- [x] Шаг 5.5: BookingPage — remind chips (1ч/2ч/3ч/6ч/12ч/24ч), npm run build OK
- [x] FAQ: исследование темы моментального загара (20+ источников: FDA, SCCS, профсалоны)
- [x] FAQ: content/faq_draft.txt — черновик 30 Q/A (одобрен)
- [x] FAQ: content/faq_spray_tan.md — финальная версия в Markdown
- [x] FAQ: backend/seed_faq.py — скрипт загрузки 30 FAQ в БД (faq_items)
- [x] FAQ: seed_faq.py выполнен — 30 записей загружены в Neon PostgreSQL (faq_items)
- [x] FAQ: верификация — все 3 файла проверены, содержание идентично, модель и API совпадают

---

## СОЗДАННЫЕ ФАЙЛЫ

```
backend/app/main.py           - FastAPI + aiogram запуск
backend/app/core/config.py    - настройки из .env
backend/app/core/database.py  - SQLAlchemy async engine
backend/app/bot/bot_instance.py - экземпляр Bot (singleton)
backend/app/bot/handlers.py   - /start с кнопкой Mini App
backend/app/bot/notifications.py - уведомления админам + клиентам
backend/app/bot/scheduler.py  - напоминания + утренняя сводка
backend/app/models/models.py  - 6 таблиц SQLAlchemy
backend/app/api/salon.py      - GET /api/salon, GET /api/faq
backend/app/api/users.py      - POST /api/users/auth
backend/app/api/services.py   - GET /api/services/
backend/app/api/slots.py      - GET/POST/PATCH слоты
backend/app/api/bookings.py   - POST/GET/PATCH записи
backend/app/api/deps.py       - проверка админа (require_admin)
backend/app/api/expenses.py   - GET/POST/DELETE расходы
backend/app/schemas/schemas.py - Pydantic модели
backend/seed_faq.py           - seed 30 FAQ в БД
backend/requirements.txt      - зависимости Python
content/faq_draft.txt         - черновик FAQ (для редактирования)
content/faq_spray_tan.md      - финальный FAQ (30 Q/A)
content/salon_info.txt        - адрес, телефон, Instagram
docker-compose.yml             - PostgreSQL 16
.env                           - секреты
.env.example                   - шаблон
.gitignore                     - исключения git
```

---

## РЕШЕНИЯ

| Что | Решение | Почему |
|-----|---------|--------|
| Формат | Telegram Mini App | UI + нет барьера установки |
| Backend | Python + FastAPI | Простой, быстрый |
| БД | PostgreSQL (Neon) | Бесплатно, надежно |
| Бот | aiogram 3 | Лучший для Python |
| Хостинг | Vercel + Railway + Neon | 0 руб/мес |
| Архитектура | DOE | Чёткое разделение ответственности |

---

## ПЛАН (5 шагов)

### Шаг 1: Бот + структура - ГОТОВ
### Шаг 2: Backend API - ГОТОВ
- 11 эндпоинтов, полный flow протестирован
### Шаг 3: Mini App (Frontend) - ГОТОВ
- 5 страниц (+ StatsPage), календарь на месяц, админ-панель + статистика доходов/расходов
### Шаг 4: Уведомления админам — ГОТОВ
- bot_instance.py, notifications.py, интеграция в bookings.py
### Шаг 5: Уведомления клиентам — ГОТОВ
- Подтверждение после записи, напоминание за N часов (клиент выбирает), утренняя сводка в 8:00

---

## ДЕПЛОЙ — ГОТОВ
- **GitHub**: https://github.com/artshumm/chocoo-skin (публичный)
- **Backend**: https://chocoo-skin-production.up.railway.app (FastAPI + aiogram + scheduler)
- **Frontend**: https://harmonious-purpose-production-8564.up.railway.app (React + Vite)
- **БД**: Neon PostgreSQL (без изменений)
- Railway Project: loyal-flexibility
- Backend Service ID: c4c71247-3fe6-4331-825b-ba13058b9c6d
- Frontend Service ID: fe7dec50-592e-4dff-adfc-c7bbac43a224

## ПОСТ-ДЕПЛОЙ ФИКСЫ (2026-02-06)
- [x] Автозавершение записей через 30 мин после начала слота (scheduler.py)
- [x] Фильтрация прошедших слотов для клиента (slots.py, 30мин cutoff)
- [x] Валидация при создании записи — нельзя записаться на прошедшее время (bookings.py)
- [x] Админ не может открыть прошедший слот (slots.py, проверка по текущему времени без 30мин)
- [x] Тестовые записи админов удалены, слоты освобождены
- [x] Утренняя сводка исключает записи админов (scheduler.py, User.role != admin)

---

## АУДИТ БЕЗОПАСНОСТИ (2026-02-06) — ВСЕ ИСПРАВЛЕНО

### Сессия 1 (HMAC + IDOR + CORS)
| # | Проблема | Статус |
|---|----------|--------|
| 1 | Telegram ID не верифицируется (HMAC-SHA256) | ✅ telegram_auth.py |
| 2-5 | IDOR (записи, отмена, профиль, body) | ✅ user из initData подписи |
| 6 | CORS allow_origins=["*"] | ✅ MINI_APP_URL only |
| 9 | Нет ограничений на длину строк | ✅ BookingCreate gt=0, SlotUpdate regex |
| 11 | Hardcoded DB credentials | ✅ database_url обязателен из .env |

### Сессия 2 (Race conditions + Production hardening)
| # | Проблема | Статус |
|---|----------|--------|
| 12 | Race condition на cancel booking | ✅ with_for_update() |
| 13 | Calendar локальное время вместо Минска | ✅ nowMinsk() UTC+3 |
| 14 | Scheduler ошибки не изолированы | ✅ отдельный try/except |
| 15 | Graceful shutdown | ✅ asyncio.gather + return_exceptions |
| 16 | Нет /health endpoint | ✅ /health + DB check |
| 17 | Нет security headers | ✅ X-Frame-Options, nosniff, Referrer |
| 18 | HomePage нет .catch() | ✅ error state |
| 19 | App.tsx auth error молчит | ✅ authError state, safe user prop |
| 20 | Expense amount без верхней границы | ✅ le=999999.99 |
| 21 | Expense month невалидный | ✅ pattern 01-12 |
| 22 | Нет DB индексов | ✅ booking(status,client_id,reminded), slot(date,status) |
| 23 | Slot unique constraint | ✅ uq_slot_datetime |
| 24 | pool_recycle отсутствует | ✅ 1800 сек |
| 25 | Слоты на прошлые даты | ✅ проверка в generate |
| 26 | Sourcemaps в production | ✅ sourcemap: false |
| 27 | useEffect cleanup | ✅ clearTimeout |
| 28 | Нет пагинации | ✅ bookings/all skip+limit |
| 29 | uvicorn reload=True | ✅ убран reload |

### Оставшееся (LOW priority, не блокирует)
- [ ] Rate limiting (slowapi) — для MVP не критично
- [ ] Alembic миграции — пока create_all достаточно

---

## ПРОИЗВОДИТЕЛЬНОСТЬ — ИСПРАВЛЕНО

| Параметр | Значение | Статус |
|----------|----------|--------|
| DB pool | pool_size=5, max_overflow=10, pool_pre_ping=True, pool_recycle=1800 | ✅ |
| Индексы | booking(status, client_id, status+reminded), slot(date+status), slot unique | ✅ |
| Пагинация | bookings/all: skip+limit (default 100, max 500) | ✅ |
| Uvicorn | reload убран из __main__ | ✅ |
| Scheduler | ошибки изолированы, date filter на auto_complete | ✅ |

---

## RAILWAY ДЕПЛОЙ — ВАЖНО
- **ВСЕГДА** передавать полный `commitSha` (40 символов) в `serviceInstanceDeploy`
- Без commitSha или с коротким SHA деплоит стейл/начальный коммит
- Backend Service ID: `c4c71247-3fe6-4331-825b-ba13058b9c6d`
- Frontend Service ID: `fe7dec50-592e-4dff-adfc-c7bbac43a224`
- Environment ID: `628cf18a-08a6-4255-9085-0259c75231e5`

## ЧТО МОЖЕТ СЛОМАТЬСЯ
1. .env путь: config.py ищет .env в корне проекта — на Railway не проблема
2. ADMIN_IDS: 446746688,412062038 — настроены
3. Neon: ssl=require обязателен в DATABASE_URL
4. Bot singleton: bot_instance.py используется и в main.py, notifications.py, scheduler.py
5. Scheduler: перезапуск сервера в 8:00 → возможен дубль утренней сводки
6. VITE_API_URL — build-time, при смене backend URL нужен redeploy frontend
