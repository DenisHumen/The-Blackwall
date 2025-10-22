# Firewall Manager - Полный План Проекта

> **Дата создания:** 23 октября 2025 г.  
> **Технологии:** Python + Rust + React + PostgreSQL + TimescaleDB

---

## 📋 Содержание

- [Архитектура системы](#архитектура-системы)
- [База данных](#база-данных)
- [Структура проекта](#структура-проекта)
- [Поток данных](#поток-данных)
- [Технические детали](#технические-детали)
- [Оптимизация](#оптимизация)
- [Безопасность](#безопасность)
- [Тестирование](#тестирование)
- [Развертывание](#развертывание)
- [План разработки](#план-разработки)
- [Roadmap](#roadmap)

---

## Архитектура системы

### Общая схема

```text
┌─────────────────────────────────────────────────┐
│           Frontend (React + TS)                 │
│  - Dashboard, Rules, Logs, Users, Analytics     │
└───────────────┬─────────────────────────────────┘
                │ REST API / WebSocket
┌───────────────▼─────────────────────────────────┐
│         Python Backend (FastAPI)                │
│  - API endpoints                                │
│  - Бизнес-логика                                │
│  - Аутентификация/авторизация                   │
│  - Управление правилами                         │
│  - ORM (SQLAlchemy)                             │
└──────┬──────────────────────────┬───────────────┘
       │                          │
       │ Python bindings          │ Direct DB Write
       ▼                          ▼
┌──────────────────┐    ┌────────────────────────┐
│  Rust Core       │    │  Rust Traffic Monitor  │
│  - nftables API  │◄───┤  - Packet capture      │
│  - ipset         │    │  - Deep inspection     │
│  - Firewall ops  │    │  - Pattern detection   │
└──────────────────┘    │  - Metrics collection  │
                        │  - Автоблокировка      │
                        │  - Batch DB inserts    │
                        └───────────┬────────────┘
                                    │
                        ┌───────────▼────────────┐
                        │   PostgreSQL 15+       │
                        │   + TimescaleDB 2.x    │
                        └────────────────────────┘
```

---

## База данных

### PostgreSQL + TimescaleDB

#### 1. Аутентификация и пользователи

**users** - учетные записи

- Поля: `id`, `username`, `email`, `password_hash`, `role`, `is_approved`, `is_active`, `created_at`, `last_login`
- Роли: `root`, `admin`, `operator`, `viewer`
- Индексы: `username`, `email`

**sessions** - активные сессии

- Поля: `id`, `user_id`, `token_hash`, `ip_address`, `user_agent`, `expires_at`, `is_active`
- Для invalidation JWT токенов
- Индексы: `user_id`, `token_hash`, `expires_at`

#### 2. Firewall правила

**firewall_rules** - все правила

- Поля: `id`, `name`, `description`, `action` (accept/drop/reject), `priority`
- Source: `source_ip` (CIDR), `source_country`, `source_port`
- Destination: `dest_ip`, `dest_port`
- Protocol: tcp/udp/icmp/any
- Metadata: `is_enabled`, `is_system`, `log_enabled`, `rate_limit`
- Tracking: `created_by`, `created_at`, `updated_at`, `applied_at`
- Statistics: `match_count`, `last_match_at`
- Индексы: `is_enabled`, `priority`, `source_ip` (GIST)

#### 3. Блокировки

**blocked_ips** - заблокированные адреса

- Поля: `id`, `ip_address`, `reason`, `block_type` (temporary/permanent)
- Auto-block: `trigger_rule_id`, `violation_count`
- Timing: `blocked_at`, `expires_at`, `unblocked_at`
- Metadata: `blocked_by`, `country_code`, `asn`, `notes`, `is_active`
- Индексы: `ip_address`, `is_active+expires_at`

#### 4. Логи и метрики (TimescaleDB hypertables)

**firewall_logs** - все события (hypertable по time)

- Поля: `time`, `source_ip`, `source_port`, `dest_ip`, `dest_port`, `protocol`
- Action: `action`, `rule_id`, `rule_name`
- Packet: `packet_size`, `ttl`, `flags`
- Metadata: `country_code`, `asn`, `threat_level`, `extra_data` (JSONB)
- Retention policy: 30 дней
- Индексы: `time`, `source_ip+time`, `action+time`, `rule_id+time`
- Continuous aggregates: по минутам, часам, дням

**traffic_metrics** - метрики производительности (hypertable)

- Traffic: `packets_in/out`, `bytes_in/out`
- Connections: `connections_active`, `connections_new`, `connections_closed`
- Firewall: `packets_dropped`, `packets_accepted`, `packets_rejected`
- System: `cpu_usage`, `memory_usage`
- Additional: `metrics_data` (JSONB)
- Retention: 7 дней raw, 90 дней агрегаты
- Continuous aggregates: 1min, 5min, 1hour

**top_talkers** - самые активные IP (hypertable)

- Поля: `time`, `ip_address`, `packets`, `bytes`, `connections`
- Metadata: `country_code`, `asn`, `is_suspicious`
- Retention: 24 часа
- Для dashboard виджетов

#### 5. Аудит и настройки

**audit_log** - история действий

- Поля: `id`, `time`, `user_id`, `username`, `action`, `resource_type`, `resource_id`
- Request: `ip_address`, `user_agent`
- Changes: `old_value` (JSONB), `new_value` (JSONB)
- Result: `success`, `error_message`
- Индексы: `time`, `user_id+time`, `action+time`

**system_settings** - конфигурация

- Поля: `key`, `value` (JSONB), `description`, `updated_by`, `updated_at`
- Настройки: `brute_force_threshold`, `port_scan_threshold`, `auto_unblock`, retention policies

**backup_history** - история backup'ов

- Поля: `id`, `backup_type`, `file_path`, `file_size`, `created_by`, `created_at`, `notes`

---

## Структура проекта

```text
firewall-manager/
│
├── rust-core/                           # Rust модули (производительность)
│   ├── Cargo.toml
│   ├── src/
│   │   ├── lib.rs
│   │   ├── nftables/                    # Управление nftables
│   │   │   ├── mod.rs
│   │   │   ├── rules.rs                 # CRUD правил
│   │   │   ├── tables.rs                # Управление таблицами
│   │   │   ├── chains.rs                # Цепочки правил
│   │   │   └── sets.rs                  # ipset управление
│   │   ├── traffic/                     # Обработка трафика
│   │   │   ├── mod.rs
│   │   │   ├── capture.rs               # Захват пакетов (libpcap/AF_PACKET)
│   │   │   ├── analyzer.rs              # Анализ паттернов
│   │   │   ├── parser.rs                # Парсинг протоколов
│   │   │   └── metrics.rs               # Сбор метрик в памяти
│   │   ├── autoblock/                   # Автоматическая блокировка
│   │   │   ├── mod.rs
│   │   │   ├── bruteforce.rs            # SSH/auth brute-force
│   │   │   ├── portscan.rs              # Port scan detection
│   │   │   ├── ddos.rs                  # DDoS mitigation (опц.)
│   │   │   └── patterns.rs              # Pattern matching engine
│   │   ├── database/                    # Direct DB access (tokio-postgres)
│   │   │   ├── mod.rs
│   │   │   ├── pool.rs                  # Connection pool (deadpool)
│   │   │   ├── logs.rs                  # Batch insert логов
│   │   │   ├── metrics.rs               # Batch insert метрик
│   │   │   ├── blocked.rs               # Управление blocked_ips
│   │   │   └── queries.rs               # Prepared statements
│   │   ├── geoip/                       # GeoIP lookup (опционально)
│   │   │   ├── mod.rs
│   │   │   └── maxmind.rs               # MaxMind DB reader
│   │   └── bindings/                    # Python bindings (PyO3)
│   │       ├── mod.rs
│   │       ├── firewall.rs              # Firewall operations
│   │       ├── monitor.rs               # Metrics/monitoring
│   │       └── config.rs                # Configuration
│   └── benches/                         # Performance benchmarks
│
├── backend/                             # Python Backend (FastAPI)
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── alembic/                         # DB миграции
│   │   ├── versions/
│   │   │   ├── 001_initial_schema.py
│   │   │   ├── 002_add_timescaledb.py
│   │   │   └── 003_audit_log.py
│   │   ├── env.py
│   │   └── alembic.ini
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                      # FastAPI application
│   │   ├── database.py                  # SQLAlchemy setup + session
│   │   ├── config.py                    # Settings (pydantic BaseSettings)
│   │   ├── api/                         # API routes
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                  # Login, register, logout, refresh
│   │   │   ├── users.py                 # CRUD users, approve/reject
│   │   │   ├── rules.py                 # CRUD firewall rules
│   │   │   ├── blocked.py               # Blocked IPs management
│   │   │   ├── logs.py                  # Search/filter logs, export
│   │   │   ├── metrics.py               # Aggregated metrics, charts data
│   │   │   ├── analytics.py             # Advanced analytics queries
│   │   │   ├── monitor.py               # WebSocket real-time metrics
│   │   │   ├── audit.py                 # Audit log viewing
│   │   │   ├── settings.py              # System settings
│   │   │   └── backup.py                # Backup/restore endpoints
│   │   ├── core/                        # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── firewall.py              # Wrapper над Rust core
│   │   │   ├── auth.py                  # JWT, password hashing, permissions
│   │   │   ├── security.py              # RBAC, decorators
│   │   │   └── notifications.py         # Email/webhook alerts (опц.)
│   │   ├── models/                      # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── base.py                  # Base model
│   │   │   ├── user.py                  # User, Session models
│   │   │   ├── rule.py                  # FirewallRule model
│   │   │   ├── blocked_ip.py            # BlockedIP model
│   │   │   ├── log.py                   # FirewallLog model (hypertable)
│   │   │   ├── metric.py                # TrafficMetric, TopTalker models
│   │   │   ├── audit.py                 # AuditLog model
│   │   │   ├── setting.py               # SystemSetting model
│   │   │   └── backup.py                # BackupHistory model
│   │   ├── schemas/                     # Pydantic schemas (validation)
│   │   │   ├── __init__.py
│   │   │   ├── user.py                  # UserCreate, UserUpdate, UserResponse
│   │   │   ├── auth.py                  # Login, Token, Register
│   │   │   ├── rule.py                  # RuleCreate, RuleUpdate, RuleResponse
│   │   │   ├── blocked_ip.py            # BlockedIPCreate, BlockedIPResponse
│   │   │   ├── log.py                   # LogSearch, LogResponse, LogExport
│   │   │   ├── metric.py                # MetricResponse, ChartData
│   │   │   └── monitor.py               # RealtimeMetrics (WebSocket)
│   │   ├── crud/                        # Database operations
│   │   │   ├── __init__.py
│   │   │   ├── base.py                  # Base CRUD class
│   │   │   ├── user.py                  # User CRUD operations
│   │   │   ├── rule.py                  # Rule CRUD operations
│   │   │   ├── blocked_ip.py            # BlockedIP operations
│   │   │   ├── log.py                   # Complex log queries, aggregations
│   │   │   ├── metric.py                # Metric queries, time-series
│   │   │   ├── analytics.py             # Advanced analytics queries
│   │   │   └── audit.py                 # Audit log queries
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   ├── backup.py                # Backup/restore logic
│   │   │   ├── query_builder.py         # SQL query helpers
│   │   │   ├── validators.py            # Custom validators (IP, CIDR)
│   │   │   ├── formatters.py            # Data formatting (bytes, dates)
│   │   │   └── export.py                # CSV/JSON export utilities
│   │   └── workers/                     # Background tasks (опц.)
│   │       ├── __init__.py
│   │       ├── cleanup.py               # Expired blocks cleanup
│   │       └── aggregation.py           # Periodic aggregations
│   ├── tests/                           # Unit tests
│   │   ├── test_api/
│   │   ├── test_crud/
│   │   └── test_core/
│   └── cli.py                           # CLI tool (Typer)
│
├── frontend/                            # React Frontend
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── vite-env.d.ts
│   │   ├── pages/                       # Страницы приложения
│   │   │   ├── Login.tsx                # Вход в систему
│   │   │   ├── Dashboard.tsx            # Главная: графики, статистика
│   │   │   ├── Rules.tsx                # Управление правилами
│   │   │   ├── BlockedIPs.tsx           # Заблокированные IP
│   │   │   ├── Logs.tsx                 # Просмотр логов с поиском
│   │   │   ├── Analytics.tsx            # Расширенная аналитика
│   │   │   ├── Users.tsx                # Управление пользователями (Root)
│   │   │   ├── Audit.tsx                # Audit log (Admin+)
│   │   │   └── Settings.tsx             # Настройки системы
│   │   ├── components/                  # Переиспользуемые компоненты
│   │   │   ├── ui/                      # shadcn/ui компоненты
│   │   │   ├── Layout.tsx               # Основной layout с навигацией
│   │   │   ├── Navbar.tsx               # Top navbar
│   │   │   ├── Sidebar.tsx              # Side menu
│   │   │   ├── ProtectedRoute.tsx       # Route guard
│   │   │   ├── RuleForm.tsx             # Форма создания/редактирования правила
│   │   │   ├── RuleTable.tsx            # Таблица правил
│   │   │   ├── RuleCard.tsx             # Карточка правила
│   │   │   ├── LogTable.tsx             # Таблица логов с пагинацией
│   │   │   ├── LogSearch.tsx            # Расширенный поиск логов
│   │   │   ├── LogFilters.tsx           # Quick filters (last hour, 24h)
│   │   │   ├── MetricsCard.tsx          # Карточка метрики
│   │   │   ├── MetricsChart.tsx         # График метрик (Recharts)
│   │   │   ├── TrafficChart.tsx         # График трафика
│   │   │   ├── RealtimeMetrics.tsx      # Real-time виджет
│   │   │   ├── TopTalkers.tsx           # Top IP addresses widget
│   │   │   ├── CountryMap.tsx           # Geo-distribution (опц.)
│   │   │   ├── BlockedIPTable.tsx       # Таблица blocked IPs
│   │   │   ├── BlockIPDialog.tsx        # Диалог блокировки
│   │   │   ├── UserTable.tsx            # Таблица пользователей
│   │   │   ├── UserApproval.tsx         # Pending approvals
│   │   │   └── ExportButton.tsx         # Кнопка экспорта данных
│   │   ├── api/                         # API клиент
│   │   │   ├── client.ts                # Axios instance с interceptors
│   │   │   ├── websocket.ts             # WebSocket manager
│   │   │   ├── auth.ts                  # Auth API calls
│   │   │   ├── rules.ts                 # Rules API calls
│   │   │   ├── logs.ts                  # Logs API calls
│   │   │   ├── metrics.ts               # Metrics API calls
│   │   │   └── users.ts                 # Users API calls
│   │   ├── hooks/                       # Custom React hooks
│   │   │   ├── useAuth.ts               # Authentication state
│   │   │   ├── useRules.ts              # Rules management
│   │   │   ├── useLogs.ts               # Log queries
│   │   │   ├── useMetrics.ts            # Metrics queries
│   │   │   ├── useWebSocket.ts          # WebSocket connection
│   │   │   ├── useDebounce.ts           # Debounce helper
│   │   │   └── usePagination.ts         # Pagination helper
│   │   ├── store/                       # State management (Zustand)
│   │   │   ├── authStore.ts             # Auth state
│   │   │   ├── rulesStore.ts            # Rules cache
│   │   │   └── settingsStore.ts         # UI settings (theme, lang)
│   │   ├── types/                       # TypeScript types
│   │   │   ├── index.ts
│   │   │   ├── api.ts                   # API response types
│   │   │   ├── models.ts                # Domain models
│   │   │   └── enums.ts                 # Enums (Action, Role, etc)
│   │   └── utils/                       # Utility functions
│   │       ├── formatters.ts            # Date, bytes, number formatting
│   │       ├── validators.ts            # Form validators
│   │       └── constants.ts             # Constants
│   └── public/
│       ├── favicon.ico
│       └── logo.svg
│
├── database/                            # Database setup
│   ├── init.sql                         # Initial schema (PostgreSQL)
│   ├── timescaledb.sql                  # TimescaleDB setup
│   ├── indexes.sql                      # Index creation
│   ├── functions.sql                    # Stored procedures (опц.)
│   ├── seeds.sql                        # Test data (dev only)
│   └── README.md                        # DB documentation
│
├── scripts/                             # Installation scripts
│   ├── install.sh                       # Main installer
│   ├── uninstall.sh                     # Clean removal
│   ├── setup-db.sh                      # PostgreSQL + TimescaleDB setup
│   ├── build-rust.sh                    # Rust compilation script
│   ├── build-frontend.sh                # Frontend build script
│   ├── update.sh                        # Update existing installation
│   └── backup.sh                        # Backup script
│
├── config/                              # Configuration templates
│   ├── config.example.yaml              # Main config template
│   ├── database.yaml                    # DB connection config
│   ├── systemd/                         # Systemd service files
│   │   ├── firewall-backend.service     # Python FastAPI service
│   │   ├── firewall-monitor.service     # Rust traffic monitor
│   │   └── postgresql.service           # PostgreSQL (if bundled)
│   ├── nginx/                           # Nginx configuration
│   │   ├── firewall-manager.conf        # Main site config
│   │   └── ssl.conf                     # SSL settings
│   └── logrotate/
│       └── firewall-manager             # Log rotation config
│
├── docs/                                # Documentation
│   ├── README.md
│   ├── INSTALL.md                       # Installation guide
│   ├── API.md                           # API documentation
│   ├── DATABASE.md                      # Database schema
│   ├── DEPLOYMENT.md                    # Deployment guide
│   ├── DEVELOPMENT.md                   # Development setup
│   └── TROUBLESHOOTING.md               # Common issues
│
├── docker/                              # Docker setup (для dev)
│   ├── Dockerfile.rust
│   ├── Dockerfile.python
│   ├── Dockerfile.postgres
│   ├── docker-compose.yml
│   └── docker-compose.dev.yml
│
├── .github/                             # CI/CD (опционально)
│   └── workflows/
│       ├── test.yml
│       └── build.yml
│
├── README.md                            # Main readme
├── LICENSE
└── .gitignore
```

---

## Поток данных

### 1. Захват и логирование трафика

```text
Сетевой пакет
  ↓
Rust Traffic Monitor (capture.rs)
  ↓ парсинг протокола
Rust Analyzer (analyzer.rs)
  ↓ проверка правил + pattern matching
Rust Autoblock (bruteforce.rs, portscan.rs)
  ↓ если нужна блокировка
Rust nftables (rules.rs) - применить блокировку
  ↓
Rust Database (logs.rs) - batch insert в firewall_logs
  ↓
PostgreSQL (firewall_logs hypertable)
  ↓ автоматические агрегации через continuous aggregates
TimescaleDB материализованные view
```

### 2. Создание правила через Web UI

```text
User заполняет RuleForm
  ↓
React отправляет POST /api/rules
  ↓
Python FastAPI (api/rules.py)
  ↓ валидация через Pydantic schema
  ↓
Python CRUD (crud/rule.py) - сохранение в DB
  ↓
PostgreSQL (firewall_rules table)
  ↓
Python Firewall Manager (core/firewall.py)
  ↓ вызов Rust через PyO3 bindings
Rust nftables (rules.rs) - применение правила
  ↓ возврат результата
Python возвращает JSON response
  ↓
React обновляет UI
```

### 3. Real-time метрики (WebSocket)

```text
Rust Traffic Monitor - собирает метрики каждую секунду
  ↓
Rust Database (metrics.rs) - batch insert каждые 5 сек
  ↓
PostgreSQL (traffic_metrics hypertable)

Параллельно:
Rust держит последние метрики в памяти
  ↓ через Python bindings
Python WebSocket endpoint (api/monitor.py)
  ↓ каждые 5 сек отправляет
React WebSocket клиент (useWebSocket hook)
  ↓
Dashboard компонент обновляется
```

### 4. Поиск в логах

```text
User вводит фильтры в LogSearch
  ↓
React отправляет GET /api/logs?source_ip=...&start_time=...
  ↓
Python FastAPI (api/logs.py)
  ↓
Python CRUD (crud/log.py) - построение SQL запроса
  ↓ использует индексы (source_ip, time)
PostgreSQL (firewall_logs hypertable)
  ↓ быстрая выборка благодаря TimescaleDB
Python возвращает JSON (пагинированный)
  ↓
React LogTable отображает результаты
```

### 5. Аналитика (агрегированные данные)

```text
User открывает Analytics страницу
  ↓
React запрашивает GET /api/analytics/traffic-by-hour
  ↓
Python FastAPI (api/analytics.py)
  ↓
Python CRUD (crud/analytics.py)
  ↓ запрос к continuous aggregate
SELECT * FROM traffic_metrics_1min WHERE bucket > ...
  ↓
TimescaleDB возвращает агрегированные данные
  ↓
Python форматирует для графиков
  ↓
React Recharts отрисовывает графики
```

---

## Технические детали

### Rust: Performance-critical компоненты

#### Зависимости

```toml
[dependencies]
# Async runtime
tokio = { version = "1.35", features = ["full"] }

# Database
tokio-postgres = "0.7"
deadpool-postgres = "0.12"

# Networking
pnet = "0.34"              # Packet capture
libc = "0.2"               # Low-level networking

# nftables
nftnl = "0.6"

# Serialization
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"

# Python bindings
pyo3 = { version = "0.20", features = ["extension-module"] }

# Utilities
chrono = "0.4"
ipnetwork = "0.20"
anyhow = "1.0"
thiserror = "1.0"

# GeoIP (optional)
maxminddb = "0.23"

# Logging
tracing = "0.1"
tracing-subscriber = "0.3"
```

#### Ключевые модули

**1. Traffic Capture (высокопроизводительный)**

- Использует AF_PACKET (Linux) или libpcap
- Zero-copy где возможно
- Ring buffer для пакетов
- Batch processing (обработка пачками)

**2. Pattern Matching Engine**

- State machine для detection
- Sliding window для rate limiting
- Bloom filters для быстрой проверки IP
- LRU cache для частых проверок

**3. Database Writer**

- Batch insert (1000-10000 записей за раз)
- Отдельный thread для DB операций
- Buffering в памяти
- Backpressure handling

**4. Memory Management**

- Fixed-size buffers для логов/метрик
- Arena allocator для packet parsing
- Object pooling для frequently allocated structures

### Python: Business Logic & API

#### Структура FastAPI приложения

```text
FastAPI app initialization
├── CORS middleware
├── Authentication middleware
├── Rate limiting middleware
├── Logging middleware
├── Router registration
│   ├── /api/auth
│   ├── /api/rules
│   ├── /api/logs
│   ├── /api/metrics
│   ├── /api/users
│   ├── /api/blocked
│   ├── /api/analytics
│   ├── /api/settings
│   └── /ws/metrics (WebSocket)
├── Exception handlers
└── Startup/Shutdown events
    ├── Database connection pool
    ├── Rust core initialization
    └── Background tasks
```

#### Database Session Management

- Connection pooling (SQLAlchemy)
- Session per request pattern
- Automatic commit/rollback
- Read replicas support (опционально)

#### Background Tasks

- Expired blocks cleanup (каждые 5 минут)
- Database vacuum (раз в день)
- Backup creation (по расписанию)
- Statistics aggregation (каждый час)

### Frontend: React Architecture

#### State Management Strategy

**Zustand stores:**

```text
authStore
├── user
├── token
├── isAuthenticated
└── permissions

rulesStore
├── rules (cached)
├── selectedRule
└── filters

settingsStore
├── theme (light/dark)
├── language
├── refreshInterval
└── notifications
```

**React Query для API:**

- Автоматический refetch
- Optimistic updates
- Cache invalidation
- Error retry logic

#### Component Hierarchy

**Dashboard**

```text
Dashboard
├── MetricsGrid
│   ├── MetricCard (Total packets)
│   ├── MetricCard (Accepted)
│   ├── MetricCard (Dropped)
│   └── MetricCard (Active connections)
├── TrafficChart (последний час)
├── TopTalkers (top 10 IPs)
├── RecentLogs (последние 20)
└── QuickActions
    ├── Block IP button
    └── Add Rule button
```

**Rules Management**

```text
Rules
├── RulesToolbar
│   ├── Search input
│   ├── Filter dropdowns
│   └── Add Rule button
├── RulesTable
│   └── RuleRow (для каждого правила)
│       ├── Rule info
│       ├── Enable/Disable toggle
│       ├── Edit button
│       ├── Delete button
│       └── Stats (match_count)
└── RuleDialog (modal)
    └── RuleForm
        ├── Basic info (name, description)
        ├── Source section (IP, country, port)
        ├── Destination section
        ├── Protocol selector
        ├── Action selector
        └── Advanced options (rate limit, logging)
```

**Logs Viewer**

```text
Logs
├── LogSearch (расширенный поиск)
│   ├── IP input
│   ├── Action selector
│   ├── Date range picker
│   ├── Quick filters (last hour, 24h, 7d)
│   └── Search/Reset buttons
├── LogTable
│   ├── Column headers (sortable)
│   ├── LogRow (для каждой записи)
│   └── Empty state
├── Pagination controls
└── Export button (CSV/JSON)
```

**Analytics**

```text
Analytics
├── SummaryCards
│   ├── Total packets (24h)
│   ├── Accepted
│   ├── Dropped
│   └── Total traffic
├── ChartsGrid
│   ├── TrafficOverTime (line chart)
│   ├── ActionDistribution (pie chart)
│   ├── TopBlockedIPs (bar chart)
│   ├── ProtocolDistribution (donut chart)
│   ├── CountryHeatmap (опц.)
│   └── HourlyActivity (heatmap)
└── TimeRangeSelector (1h, 24h, 7d, 30d, custom)
```

---

## Оптимизация

### Database Level

**Индексирование:**

- Partial indexes: `CREATE INDEX idx_active_blocks ON blocked_ips(ip_address) WHERE is_active = true`
- Expression indexes: `CREATE INDEX idx_log_hour ON firewall_logs((time::date))`
- BRIN indexes: для больших time-series таблиц (опц.)

**Query Optimization:**

- Prepared statements везде
- EXPLAIN ANALYZE для всех сложных запросов
- Избегать N+1 queries (eager loading)
- Использовать COUNT(*) OVER() для пагинации

**TimescaleDB Features:**

- Compression для старых данных (>7 дней)
- Continuous aggregates для dashboard
- Data retention policies
- Chunk size tuning (1 день для logs, 1 час для metrics)

### Rust Level

**Memory:**

- Stack allocation где возможно
- Vec capacity pre-allocation
- String interning для rule names
- Memory-mapped files для GeoIP DB

**Concurrency:**

- Lock-free structures где возможно
- Read-write locks вместо Mutex
- Channel-based communication между threads
- Work stealing для parallel processing

**Network:**

- Kernel bypass через AF_PACKET + PACKET_MMAP
- Batch syscalls
- Zero-copy packet processing
- Hardware offloading (если доступно)

### Python Level

**API Performance:**

- Response compression (gzip)
- HTTP/2 support через uvicorn
- Connection pooling
- Query result caching (Redis - опц.)

**Database:**

- Connection pooling (min=5, max=20)
- Lazy loading relationships
- Bulk operations где возможно
- Async database driver (asyncpg - опц.)

### Frontend Level

**Bundle Size:**

- Code splitting по routes
- Lazy loading компонентов
- Tree shaking
- Asset compression

**Runtime:**

- Virtual scrolling для больших таблиц
- Debounce для search inputs
- Memo/useMemo для expensive calculations
- Web Workers для heavy processing (опц.)

**Network:**

- Request deduplication
- GraphQL batching (если используется)
- Service Worker для offline support (опц.)
- CDN для static assets (production)

---

## Безопасность

### Application Security

**Authentication:**

- JWT с коротким TTL (15 мин access, 7 дней refresh)
- Token rotation
- Secure password hashing (bcrypt, rounds=12)
- Rate limiting на /login (5 попыток за 5 минут)
- Session invalidation при logout

**Authorization:**

- RBAC на уровне API endpoints
- Row-level security в DB (опц.)
- Audit всех критичных действий
- Principle of least privilege

**Input Validation:**

- Pydantic schemas для всех inputs
- IP/CIDR validation
- SQL injection prevention (ORM + prepared statements)
- XSS prevention (React escaping)
- CSRF tokens

**API Security:**

- CORS whitelist
- Rate limiting (100 req/min per IP)
- Request size limits
- Timeout для long-running requests

### Infrastructure Security

**Database:**

- Encrypted connections (TLS)
- Separate user для read-only operations
- Regular backups (encrypted)
- No superuser access from app

**Network:**

- Firewall runs on separate VM/interface
- Management interface на отдельном порту
- SSL/TLS для web interface (Let's Encrypt)
- No direct DB access from internet

**System:**

- Run services as non-root user
- AppArmor/SELinux profiles
- Minimal installed packages
- Regular security updates

---

## Тестирование

### Unit Tests

**Rust:**

- nftables operations (mocked)
- Pattern matching logic
- Packet parsing
- Database queries (с test DB)

**Python:**

- CRUD operations
- Business logic
- Validators
- Utility functions

**Frontend:**

- Component rendering
- User interactions
- Form validation
- API client functions

### Integration Tests

**API Tests:**

- Auth flow (login, refresh, logout)
- CRUD endpoints
- WebSocket connections
- Error handling
- Permission checks

**Database Tests:**

- Complex queries
- Aggregations
- Retention policies
- Backup/restore

### E2E Tests

**Critical User Flows:**

- Login → Create rule → Verify applied
- View logs → Filter → Export
- Block IP → Verify blocked → Unblock
- Dashboard loads → Real-time updates work

**Tools:**

- Playwright для frontend E2E
- pytest для Python
- cargo test для Rust

---

## Развертывание

### Минимальные требования

**Hardware:**

- CPU: 2 cores (4 recommended)
- RAM: 4GB (8GB recommended)
- Disk: 50GB SSD
- Network: 1Gbps interface

**Software:**

- Ubuntu Server 24.04 LTS
- PostgreSQL 15+
- TimescaleDB 2.x
- nftables (kernel 5.x+)
- Python 3.11+
- Rust 1.75+ (для сборки)
- Node.js 20+ (для сборки frontend)

### Production Deployment

**Architecture:**

```text
Internet
   ↓
Nginx (reverse proxy + SSL)
   ↓
FastAPI (Python backend) - systemd service
   ↓
PostgreSQL + TimescaleDB - systemd service
   ↑
Rust Monitor - systemd service (direct DB write)
```

**Systemd Services:**

- `firewall-backend.service` (Python API)
- `firewall-monitor.service` (Rust traffic monitor)
- `postgresql.service` (Database)
- `nginx.service` (Web server)

**Monitoring:**

- systemd logs: `journalctl -u firewall-*`
- Application logs: `/var/log/firewall-manager/`
- Database logs: `/var/log/postgresql/`

---

## План разработки

### Сроки разработки (1 разработчик)

| Этап | Компонент | Время |
|------|-----------|-------|
| 1 | PostgreSQL schema + TimescaleDB setup | 3-5 дней |
| 2 | Rust Core (nftables, ipset, bindings) | 2-3 недели |
| 3 | Rust Traffic Monitor (capture, analyze) | 2-3 недели |
| 4 | Rust Database integration (batch inserts) | 1 неделя |
| 5 | Python Backend (API, auth, CRUD) | 2-3 недели |
| 6 | Python-Rust integration | 3-5 дней |
| 7 | React Frontend (все страницы) | 2-3 недели |
| 8 | WebSocket real-time updates | 3-5 дней |
| 9 | Analytics страница + сложные запросы | 1 неделя |
| 10 | CLI инструмент | 3-5 дней |
| 11 | Install/Uninstall scripts | 1 неделя |
| 12 | Systemd services + nginx config | 3-5 дней |
| 13 | Testing + Bug fixes | 1-2 недели |
| 14 | Documentation | 3-5 дней |

**Итого:** 11-15 недель (2.5-4 месяца)

### Приоритизация (поэтапный план)

#### Phase 1: Core Infrastructure (3-4 недели)

**Цель:** Базовая функциональность без UI

- PostgreSQL + TimescaleDB setup
  - Создание всех таблиц
  - Настройка hypertables
  - Базовые индексы
- Rust nftables integration
  - Добавление/удаление правил
  - Чтение текущих правил
  - Backup/restore
- Python Backend (минимальный)
  - Database models (SQLAlchemy)
  - Basic CRUD operations
  - Rust bindings integration
- CLI инструмент (базовый)
  - add-rule, delete-rule, list-rules
  - block-ip, unblock-ip

**Результат:** Можно управлять firewall через CLI

#### Phase 2: Traffic Monitoring (3-4 недели)

**Цель:** Сбор метрик и логирование

- Rust Traffic Monitor
  - Packet capture (libpcap)
  - Protocol parsing (TCP/UDP/ICMP)
  - Basic pattern matching
- Database integration
  - Batch insert логов
  - Batch insert метрик
  - Connection pooling
- Autoblock logic
  - Brute-force detection
  - Port scan detection
  - Автоматическое применение блокировок
- Python API endpoints
  - GET /api/logs (поиск)
  - GET /api/metrics (базовые)
  - GET /api/blocked-ips

**Результат:** Система собирает данные и автоматически блокирует угрозы

#### Phase 3: Web Interface (3-4 недели)

**Цель:** Полноценный веб-интерфейс

- Authentication система
  - Login/Register
  - JWT tokens
  - Session management
  - Role-based access
- Dashboard страница
  - Базовые метрики (cards)
  - Простые графики (Recharts)
  - Recent logs
- Rules страница
  - Список правил (таблица)
  - Форма создания/редактирования
  - Enable/disable toggle
  - Delete confirmation
- Blocked IPs страница
  - Список заблокированных
  - Ручная блокировка/разблокировка
  - Причины блокировки
- Logs страница
  - Таблица с пагинацией
  - Базовые фильтры (IP, action)
  - Date range picker

**Результат:** Полноценное управление через браузер

#### Phase 4: Advanced Features (2-3 недели)

**Цель:** Расширенная функциональность

- WebSocket integration
  - Real-time метрики
  - Live log updates
  - Connection status indicator
- Analytics страница
  - Top blocked IPs
  - Traffic charts (hourly/daily)
  - Action distribution (pie chart)
  - Country distribution
- Users management (Root only)
  - Approve/reject registrations
  - Role assignment
  - User activity log
- Advanced log search
  - Multiple filters
  - Time range presets
  - Export to CSV/JSON
- Audit log
  - Все действия пользователей
  - Change tracking

**Результат:** Production-ready система

#### Phase 5: Deployment & Polish (1-2 недели)

**Цель:** Готовность к развертыванию

- Install script
  - Автоматическая установка всех компонентов
  - Wizard первоначальной настройки
  - Проверка requirements
- Systemd services
  - Auto-start on boot
  - Graceful shutdown
  - Log rotation
- Nginx configuration
  - Reverse proxy
  - SSL/TLS setup
  - Static files serving
- Backup/Restore
  - Автоматический backup
  - Manual backup через CLI
  - Restore mechanism
- Documentation
  - Installation guide
  - User manual
  - API documentation
  - Troubleshooting guide

**Результат:** Готовый продукт для развертывания

---

## Roadmap

### Version 1.1 (Post-MVP)

- GeoIP блокировка с автообновлением баз
- Threat Intelligence feeds (AbuseIPDB, Shodan)
- Email/SMS уведомления
- Telegram bot для alerts
- Экспорт в Grafana dashboards

### Version 1.2

- Machine Learning anomaly detection
- DDoS mitigation (L7)
- VPN integration (WireGuard)
- Multi-node support (clustering)
- High Availability mode

### Version 2.0

- IDS/IPS capabilities (Suricata integration)
- Content filtering
- QoS management
- VLAN support
- API для интеграции с внешними системами

---

## Ключевые преимущества архитектуры

### ✅ Производительность

- Rust обрабатывает миллионы пакетов в секунду
- TimescaleDB оптимизирован для time-series
- Batch inserts минимизируют DB overhead

### ✅ Масштабируемость

- Логи и метрики партиционированы автоматически
- Retention policies предотвращают переполнение
- Read replicas для аналитики (опц.)

### ✅ Удобство разработки

- Python для быстрой разработки бизнес-логики
- Rust только там, где нужна скорость
- React для современного UI

### ✅ Надежность

- Автоматические backup'ы
- Rollback mechanism
- Audit trail для всех действий

### ✅ Безопасность

- Defense in depth
- Minimal attack surface
- Regular security updates

---

**Готов к реализации! 🚀**
