# The Blackwall

Комплексная система управления межсетевым экраном на базе Python, Rust, React и PostgreSQL.

![TheBlackWall](assets/images/TheBlackWall_4K.gif)

## Возможности

- **Аутентификация**: JWT + httpOnly cookies, rate-limiting, одноразовая первичная настройка
- **Мониторинг**: CPU, RAM, диск, сеть в реальном времени с автообновлением
- **Графики трафика**: авто-масштабирование (B/s → KB/s → MB/s → GB/s)
- **Балансировщик нагрузки**: Round-robin между провайдерами и Failover (основной/резервный)
- **Health-check**: автоматическая проверка доступности шлюзов через ping

## Архитектура

- **Frontend**: React 18 + TypeScript + Vite + TailwindCSS + Recharts + Zustand
- **Backend**: Python FastAPI + SQLAlchemy async + aiosqlite (dev) / PostgreSQL (prod)
- **Core Engine**: Rust (nftables, traffic monitoring)
- **Database**: SQLite (разработка) / PostgreSQL + TimescaleDB (production)

## Структура проекта

```
backend/          Python FastAPI backend
  app/api/        API эндпоинты (auth, metrics, loadbalancer)
  app/core/       Бизнес-логика (auth, metrics, firewall)
  app/models/     SQLAlchemy модели
  app/schemas/    Pydantic схемы
  tests/          Тесты (21 тест)
frontend/         React SPA
  src/pages/      Страницы (Login, Dashboard, LoadBalancer)
  src/components/ Компоненты (TrafficChart, MetricsCard, Layout)
  src/api/        API клиент
  src/store/      Zustand store
rust-core/        Rust модули для производительности
database/         SQL схемы и миграции
scripts/          Установочные скрипты
config/           Конфигурационные файлы
docs/             Документация
```

## Быстрый старт

```bash
# Запуск через единый лаунчер
python main.py quickstart

# Или вручную
cd backend && pip install -r requirements.txt
cd frontend && npm install && npm run build
cd backend && python -m uvicorn app.main:app --reload
```

Откройте http://localhost:8000 — при первом запуске система предложит создать root-пользователя.

## API Endpoints

| Метод   | Путь                                    | Описание                     |
|---------|-----------------------------------------|------------------------------|
| GET     | `/api/auth/setup-check`                | Проверка необходимости setup |
| POST    | `/api/auth/setup`                      | Первичная настройка          |
| POST    | `/api/auth/login`                      | Вход                         |
| POST    | `/api/auth/logout`                     | Выход                        |
| GET     | `/api/auth/me`                         | Текущий пользователь         |
| GET     | `/api/metrics/current`                 | Текущие метрики системы      |
| GET     | `/api/metrics/traffic?minutes=60`      | История трафика              |
| GET     | `/api/loadbalancer/`                   | Список конфигураций LB       |
| POST    | `/api/loadbalancer/`                   | Создать конфигурацию LB      |
| PATCH   | `/api/loadbalancer/{id}`               | Обновить конфигурацию LB     |
| DELETE  | `/api/loadbalancer/{id}`               | Удалить конфигурацию LB      |
| POST    | `/api/loadbalancer/{id}/gateways`      | Добавить шлюз                |
| DELETE  | `/api/loadbalancer/{id}/gateways/{gw}` | Удалить шлюз                 |
| POST    | `/api/loadbalancer/{id}/health-check`  | Health-check шлюзов          |

Swagger UI: http://localhost:8000/docs

## Тестирование

```bash
cd backend
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -p anyio -p asyncio tests/ -v
```

## Лицензия

MIT
