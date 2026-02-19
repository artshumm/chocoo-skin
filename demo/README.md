# Demo Shell — Chocoo Skin

Публичная демо-версия для презентации потенциальным клиентам. Работает в обычном браузере без Telegram.

## Архитектура

```
Браузер → Demo Frontend (demo.html)
              │
         DemoOverlay: [Барбершоп] [Массаж] [Автомойка] ...
         [Клиент ↔ Админ] [Сбросить] [Своё]
              │
              ▼
         Demo Backend (demo_main.py)
           ├── Все API роутеры (из app.api.*)
           ├── demo_get_user (без HMAC)
           ├── POST /api/demo/reset
           ├── GET /api/demo/presets
           └── БЕЗ бота, БЕЗ scheduler
              │
              ▼
         SQLite: demo.db
```

## Локальный запуск

### Backend

```bash
cd /path/to/project
PYTHONPATH=backend python -m demo.backend.demo_main
# Сервер на http://localhost:8001
```

Env vars (опционально, есть дефолты):
- `DEMO_DB_PATH` — путь к SQLite файлу (default: `demo.db`)
- `ADMIN_IDS` — ID админа (default: `1000002`)
- `DEMO_FRONTEND_URL` — URL фронтенда для CORS

### Frontend

```bash
cd frontend
VITE_API_URL=http://localhost:8001 npx vite --config vite.config.demo.ts --port 5174
# Открыть http://localhost:5174/demo.html
```

### Сборка фронтенда

```bash
cd frontend
VITE_API_URL=https://<demo-backend>.up.railway.app npm run build:demo
# Результат: dist-demo/
```

## Первый запуск

После запуска backend — инициализировать данные:

```bash
curl -X POST http://localhost:8001/api/demo/reset \
  -H "Content-Type: application/json" \
  -d '{"preset": "barbershop"}'
```

## Демо-пользователи

| Роль | telegram_id | username |
|------|------------|----------|
| Клиент | 1000001 | demo_client |
| Админ | 1000002 | demo_admin |

Переключение ролей — кнопка в DemoOverlay (верхняя панель).

## 10 пресетов бизнесов

| Preset ID | Ниша | Интервал слотов |
|-----------|------|----------------|
| `barbershop` | Барбершоп BLADE | 30 мин |
| `beauty` | Салон красоты Glamour | 30 мин |
| `massage` | Массажный салон Relax | 30 мин |
| `dental` | Стоматология SmileClinic | 30 мин |
| `auto_service` | Автосервис МоторПро | 60 мин |
| `car_wash` | Автомойка AquaShine | 30 мин |
| `photo` | Фотостудия LightBox | 60 мин |
| `tutor` | Репетитор ProEducation | 60 мин |
| `gaming` | Компьютерный клуб CyberZone | 60 мин |
| `hookah` | Кальянная SmokeLounge | 60 мин |

## Railway деплой

### Env vars — Demo Backend
```
BOT_TOKEN=demo_placeholder_token
ADMIN_IDS=1000002
DEMO_FRONTEND_URL=https://<demo-frontend>.up.railway.app
```

### Env vars — Demo Frontend
```
VITE_API_URL=https://<demo-backend>.up.railway.app
```

### Start commands
- Backend: `cd backend && python -m demo.backend.demo_main` (с `PYTHONPATH` настроенным в Railway)
- Frontend: `serve dist-demo -s -l ${PORT:-3000}`

## Файлы

### Новые (11 файлов)
- `demo/__init__.py` — Python package
- `demo/backend/__init__.py` — Python package
- `demo/backend/presets.py` — 10 пресетов бизнесов
- `demo/backend/demo_reset.py` — POST /api/demo/reset endpoint
- `demo/backend/demo_main.py` — FastAPI app (SQLite, без бота)
- `demo/README.md` — эта инструкция
- `frontend/demo.html` — HTML entry point (без Telegram SDK)
- `frontend/src/demo/demo-main.tsx` — Mock WebApp + React entry
- `frontend/src/demo/DemoOverlay.tsx` — Панель управления демо
- `frontend/src/demo/DemoOverlay.css` — Стили панели
- `frontend/vite.config.demo.ts` — Vite конфиг для demo build

### Модифицированные (1 файл)
- `frontend/package.json` — добавлен скрипт `build:demo`

### Core файлы НЕ менялись
Демо импортирует всё из `app.*` — обновления продукта автоматически отражаются в демо.
