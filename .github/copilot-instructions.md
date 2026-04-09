# Firewall Manager - AI Coding Agent Instructions

## Project Overview

**Firewall Manager** - это гибридная система управления межсетевым экраном, сочетающая производительность Rust с гибкостью Python/FastAPI и современным React UI.

### Ключевая архитектура

```
React (TypeScript) ←→ FastAPI (Python) ←→ Rust Core ←→ nftables/iptables
                           ↓                    ↓
                    PostgreSQL + TimescaleDB (time-series data)
```

**Критические компоненты:**
- **Rust Core** (`rust-core/src/`) - производительные модули для работы с nftables, захвата трафика, автоблокировки
- **Python Backend** (`backend/app/`) - FastAPI REST API, бизнес-логика, ORM (SQLAlchemy)
- **React Frontend** (`frontend/src/`) - SPA с реальным временем через WebSocket
- **TimescaleDB** - time-series данные для логов (`firewall_logs`), метрик (`traffic_metrics`)

## Технологический стек

### Backend (Python 3.11+)
- **FastAPI** - REST API endpoints в `backend/app/api/`
- **SQLAlchemy 2.0+** - ORM модели в `backend/app/models/`
- **Alembic** - миграции БД в `backend/alembic/versions/`
- **Pydantic 2.5+** - валидация данных в `backend/app/schemas/`
- **python-jose** - JWT аутентификация

### Rust Core
- **PyO3** - Python bindings в `rust-core/src/bindings/`
- **Crate type**: `cdylib` для Python, `rlib` для Rust
- Модули: `nftables/`, `traffic/`, `autoblock/`, `database/`, `geoip/`

### Frontend (React 18 + TypeScript)
- **Vite** - build tool
- **TailwindCSS** - стилизация
- **Zustand** - state management (легче Redux)
- **Recharts** - визуализация метрик
- **Axios** - HTTP client с interceptors в `frontend/src/api/client.ts`

### Database
- **PostgreSQL 15+** - основная БД
- **TimescaleDB 2.x** - hypertables для `firewall_logs`, `traffic_metrics`, `top_talkers`
- **Retention policies** - 30 дней для логов, 7 дней raw метрики

## Паттерны кодирования

### Backend структура

**API endpoints** (`backend/app/api/`):
```python
# Стандартный API endpoint паттерн
@router.post("/rules", response_model=schemas.RuleResponse)
async def create_rule(
    rule: schemas.RuleCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # 1. Валидация через Pydantic (schemas)
    # 2. CRUD операции через crud модуль
    # 3. Вызов Rust core для применения правила
    # 4. Audit log запись
    pass
```

**CRUD паттерн** (`backend/app/crud/`):
- Наследование от `CRUDBase` в `crud/base.py`
- Типизированные операции: `get()`, `get_multi()`, `create()`, `update()`, `delete()`
- Сложные запросы в специализированных методах (например, `log.py` для time-series queries)

**Models vs Schemas**:
- `models/` - SQLAlchemy ORM (DB tables)
- `schemas/` - Pydantic (API validation/serialization)

### Rust Core интеграция

**Python bindings** (`rust-core/src/bindings/`):
```rust
// PyO3 паттерн для экспорта функций в Python
#[pyfunction]
fn apply_firewall_rule(rule_id: i32, action: &str) -> PyResult<bool> {
    // Direct nftables manipulation
}
```

**Прямая запись в БД** из Rust:
- `rust-core/src/database/` использует `tokio-postgres` для batch inserts
- Логи и метрики пишутся напрямую (bypassing Python ORM для производительности)

### Frontend структура

**State management**:
- Zustand stores в `frontend/src/store/` для глобального состояния
- React Query/custom hooks для server state в `frontend/src/hooks/`

**API клиент** (`frontend/src/api/client.ts`):
```typescript
// Axios instance с JWT interceptors
// Автоматический refresh токенов
// Centralized error handling
```

**WebSocket** для real-time метрик:
- `frontend/src/api/websocket.ts` - WebSocket manager
- `backend/app/api/monitor.py` - WebSocket endpoint

### Database conventions

**Alembic migrations** (`backend/alembic/versions/`):
- Префикс: `001_`, `002_`, `003_` (sequential)
- Именование: `{number}_{description}.py`
- Всегда include upgrade() и downgrade()

**TimescaleDB hypertables**:
- `firewall_logs` - partitioned by `time` column
- Continuous aggregates для dashboard queries
- Retention policies автоматически удаляют старые данные

**Индексы** (`database/indexes.sql`):
- GIST индексы для CIDR/IP ranges
- Composite indexes для time-series queries: `(source_ip, time)`, `(action, time)`

## Важные рабочие процессы

### Разработка

**Backend запуск** (из `backend/`):
```bash
# Poetry/pip install
pip install -r requirements.txt

# Alembic миграции
alembic upgrade head

# Dev server
uvicorn app.main:app --reload
```

**Rust сборка**:
```bash
cd rust-core
cargo build --release
# Binary для Python: target/release/libfirewall_core.so (Linux)
```

**Frontend dev**:
```bash
cd frontend
npm install
npm run dev  # Vite dev server
```

### База данных

**Создание миграции**:
```bash
cd backend
alembic revision --autogenerate -m "description"
# Review generated file before applying!
alembic upgrade head
```

**TimescaleDB setup** (первый раз):
```bash
psql -d firewall_db -f database/timescaledb.sql
```

### Тестирование

**Python tests** (еще не реализовано):
```bash
cd backend
pytest tests/
```

## Критические детали

### Аутентификация

**JWT flow**:
1. `POST /auth/login` → JWT access token + refresh token
2. Access token в `Authorization: Bearer <token>` заголовке
3. Refresh через `POST /auth/refresh` при expiry
4. Session invalidation через `sessions` table

**RBAC** (`backend/app/core/security.py`):
- Роли: `root`, `admin`, `operator`, `viewer`
- Декораторы: `@require_role("admin")` для endpoint protection

### Firewall правила

**Приоритет** (priority):
- Меньше число = выше приоритет
- System rules (is_system=true) имеют высший приоритет

**Rate limiting**:
- `rate_limit` поле в `firewall_rules`: формат `"100/minute"`
- Применяется в Rust через nftables

### Auto-blocking логика

**Триггеры** (`rust-core/src/autoblock/`):
- Brute-force detection: threshold в `system_settings`
- Port scan detection: consecutive ports
- DDoS mitigation: packets per second threshold

**Workflow**:
1. Rust monitor детектирует угрозу
2. Запись в `blocked_ips` (прямая вставка через tokio-postgres)
3. Применение блокировки через nftables
4. WebSocket уведомление → frontend alert

### Time-series данные

**Query patterns**:
```sql
-- Использовать continuous aggregates для dashboard
SELECT * FROM firewall_logs_1hour WHERE time > NOW() - INTERVAL '24 hours';

-- NOT: SELECT * FROM firewall_logs WHERE ...  (слишком медленно)
```

**Retention policies** применяются автоматически:
- 30 дней для `firewall_logs`
- 7 дней raw, 90 дней aggregates для `traffic_metrics`

## Соглашения по коду

### Python
- **Type hints везде** (Python 3.11+ syntax)
- **Async/await** для I/O операций (DB, external calls)
- **Docstrings** в формате: кратко описание функции
- Именование: `snake_case` для функций/переменных

### Rust
- **Error handling**: `Result<T, E>` вместо panics
- **Async** для DB operations (`tokio`)
- Именование: `snake_case` для функций, `PascalCase` для types

### TypeScript
- **Strict mode** enabled
- **Interface** для data shapes, **type** для unions/helpers
- Именование: `camelCase` для переменных, `PascalCase` для components

### SQL
- **Lowercase** для ключевых слов в production code
- **Snake_case** для таблиц/колонок
- **Explicit indexes** для performance-critical queries

## Специфичные для проекта детали

### Config файлы

**Основной config** (`config/config.example.yaml`):
- Database connection string
- JWT secret/expiry
- Rust module paths
- Retention policies

**Не коммитить**:
- `config/config.yaml` (real credentials)
- `backend/.env`

### Скрипты установки

**Расположение**: `scripts/`
- `install.sh` - полная установка (Rust build, DB setup, systemd services)
- `update.sh` - обновление существующей установки
- Все скрипты должны быть idempotent

### Systemd services

**Backend** (`config/systemd/firewall-backend.service`):
- Запускает uvicorn с production settings
- Restart=always для высокой доступности

**Monitor** (`config/systemd/firewall-monitor.service`):
- Запускает Rust traffic monitor
- Requires=postgresql.service

## Типичные задачи

### Добавление нового API endpoint

1. Определить Pydantic schema в `backend/app/schemas/`
2. Создать/обновить CRUD методы в `backend/app/crud/`
3. Добавить endpoint в соответствующий router в `backend/app/api/`
4. Обновить frontend API client в `frontend/src/api/`
5. Создать/обновить React hook в `frontend/src/hooks/`

### Добавление миграции БД

1. Изменить SQLAlchemy models в `backend/app/models/`
2. Сгенерировать миграцию: `alembic revision --autogenerate`
3. Проверить сгенерированный файл (autogenerate не идеален!)
4. Применить: `alembic upgrade head`
5. Обновить `database/init.sql` для чистой установки

### Добавление Rust функционала

1. Реализовать в соответствующем модуле (`rust-core/src/nftables/`, etc)
2. Экспортировать через PyO3 bindings в `rust-core/src/bindings/`
3. Пересобрать: `cargo build --release`
4. Импортировать в Python: `from firewall_core import ...`
5. Использовать в `backend/app/core/firewall.py`

## Полезные команды

```bash
# Backend
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontend && npm run dev

# Alembic
alembic upgrade head
alembic downgrade -1
alembic history

# Rust build
cd rust-core && cargo build --release

# Database
psql -U firewall_user -d firewall_db
# Inside psql: \dt - list tables, \d table_name - describe table

# Logs
journalctl -u firewall-backend.service -f
journalctl -u firewall-monitor.service -f
```

## Важные файлы для понимания архитектуры

- `todo.md` - полный план проекта, схемы БД, детальная архитектура
- `plan/PROJECT_STRUCTURE.md` - файловая структура с описанием
- `backend/app/main.py` - точка входа FastAPI (когда реализуется)
- `rust-core/src/lib.rs` - точка входа Rust core
- `database/init.sql` - полная схема БД (когда создается)
- `frontend/src/App.tsx` - точка входа React app

## Текущее состояние проекта

Проект находится в **начальной стадии** - большинство файлов являются заглушками с комментариями. При реализации:

1. **Начать с backend**: Models → CRUD → API endpoints → Auth
2. **Затем Rust core**: nftables basics → Python bindings
3. **Frontend последним**: API client → Pages → Components
4. **Database**: Сначала базовая схема, TimescaleDB позже

Всегда проверяйте `todo.md` для детального плана и требований к каждому компоненту.
