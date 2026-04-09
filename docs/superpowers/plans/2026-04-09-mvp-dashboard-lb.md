# The Blackwall MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first working iteration of The Blackwall — auth, dashboard with real-time metrics, and load balancer management panel.

**Architecture:** FastAPI backend serves REST API + WebSocket. React/TS/Tailwind frontend. SQLite via SQLAlchemy for MVP. System metrics from /proc. Load balancer via Linux ip route/rule commands. Runs as systemd service on Ubuntu 22.04.

**Tech Stack:** Python 3.10+ (FastAPI, SQLAlchemy, python-jose, passlib), React 18 (TypeScript, Vite, TailwindCSS, Recharts), SQLite

**Spec:** `docs/superpowers/specs/2026-04-09-mvp-dashboard-lb-design.md`

---

## File Structure

```
backend/
  app/
    main.py                    — FastAPI app setup, CORS, lifespan, route mounting
    config.py                  — Pydantic Settings (SECRET_KEY, DB_URL, etc.)
    database.py                — SQLAlchemy engine, SessionLocal, Base, get_db
    models/
      base.py                  — DeclarativeBase
      __init__.py              — Re-export all models
      user.py                  — User model (id, username, password_hash, role, etc.)
      loadbalancer.py          — LBConfig + LBProvider models
    schemas/
      auth.py                  — SetupRequest, LoginRequest, UserResponse, TokenData
      metrics.py               — SystemMetrics, TrafficData, InterfaceInfo
      loadbalancer.py          — LBConfigSchema, LBProviderSchema, LBStatusSchema
    api/
      auth.py                  — POST setup/login/logout, GET me
      metrics.py               — GET /metrics/system, WS /ws/traffic
      loadbalancer.py          — CRUD providers, GET/PUT config, GET status
    core/
      auth.py                  — create_jwt, verify_jwt, hash_password, verify_password, get_current_user
      metrics.py               — parse_cpu(), parse_memory(), parse_disk(), parse_traffic()
      lb_engine.py             — apply_routes(), clear_routes(), build_multipath(), set_failover()
      lb_monitor.py            — HealthMonitor class (asyncio background task)
  tests/
    conftest.py                — pytest fixtures (test client, test db, etc.)
    test_auth.py               — Auth flow tests
    test_metrics.py            — Metric parsing tests
    test_lb_engine.py          — LB routing command tests
    test_lb_monitor.py         — Health monitor tests
    test_lb_api.py             — LB API endpoint tests
  requirements.txt             — Updated with all deps

frontend/
  package.json                 — All dependencies
  tsconfig.json                — TS config
  vite.config.ts               — Vite + proxy to backend
  tailwind.config.js           — Dark theme
  postcss.config.js            — PostCSS for Tailwind
  index.html                   — Entry HTML
  src/
    main.tsx                   — ReactDOM.createRoot
    App.tsx                    — BrowserRouter + routes
    index.css                  — Tailwind imports + global styles
    api/client.ts              — fetch wrapper with credentials
    types/index.ts             — All TS interfaces
    pages/
      LoginPage.tsx            — Login + initial setup
      DashboardPage.tsx        — Metrics dashboard
      LoadBalancerPage.tsx     — LB management
    components/
      Layout.tsx               — Sidebar nav + content area
      ServerLoad.tsx           — CPU/RAM/Disk bars
      TrafficChart.tsx         — Recharts line chart
      InterfaceList.tsx        — Network interfaces table
      ProviderTable.tsx        — LB providers table
      ProviderForm.tsx         — Add/edit provider modal
    hooks/
      useAuth.ts               — Auth state + login/logout
      useWebSocket.ts          — WS connection with reconnect

scripts/
  install.sh                   — Ubuntu 22.04 installer

config/
  systemd/blackwall.service    — Systemd unit
```

---

## Task 1: Backend Foundation — Config, Database, Base Model

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/database.py`
- Modify: `backend/app/models/base.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/requirements.txt`
- Modify: `backend/pyproject.toml`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Update requirements.txt**

```
# backend/requirements.txt
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
websockets>=12.0
sqlalchemy>=2.0.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.6
aiosqlite>=0.19.0
httpx>=0.25.0
pytest>=7.4.0
pytest-asyncio>=0.23.0
```

- [ ] **Step 2: Update pyproject.toml dependencies**

Add the same deps to pyproject.toml `dependencies` list.

- [ ] **Step 3: Install dependencies**

Run: `cd /Users/denisgumen/Desktop/code/The-Blackwall/backend && pip install -r requirements.txt`

- [ ] **Step 4: Write config.py**

```python
# backend/app/config.py
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    SECRET_KEY: str = "change-me-in-production-please"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24
    DB_URL: str = f"sqlite+aiosqlite:///{Path(__file__).parent.parent / 'blackwall.db'}"
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    class Config:
        env_prefix = "BLACKWALL_"

settings = Settings()
```

- [ ] **Step 5: Write database.py**

```python
# backend/app/database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

engine = create_async_engine(settings.DB_URL, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with SessionLocal() as session:
        yield session

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

- [ ] **Step 6: Write base.py and __init__.py**

```python
# backend/app/models/base.py
from app.database import Base
```

```python
# backend/app/models/__init__.py
from app.models.user import User
# LBConfig, LBProvider imported after Task 6 creates them
```

Create a stub `backend/app/models/loadbalancer.py`:
```python
# backend/app/models/loadbalancer.py
"""Load balancer models — implemented in Task 6"""
```

- [ ] **Step 7: Write test conftest.py**

```python
# backend/tests/conftest.py
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.database import Base, get_db
from app.main import app

TEST_DB_URL = "sqlite+aiosqlite://"

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def db_session():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
```

- [ ] **Step 8: Commit**

```bash
git add backend/requirements.txt backend/pyproject.toml backend/app/config.py backend/app/database.py backend/app/models/base.py backend/app/models/__init__.py backend/tests/conftest.py
git commit -m "feat: backend foundation — config, async database, test fixtures"
```

---

## Task 2: User Model + Auth Core

**Files:**
- Modify: `backend/app/models/user.py`
- Modify: `backend/app/core/auth.py`
- Modify: `backend/app/schemas/auth.py`
- Create: `backend/tests/test_auth.py`

- [ ] **Step 1: Write the User model**

```python
# backend/app/models/user.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    role = Column(String(20), nullable=False, default="admin")  # root|admin|operator|viewer — not enforced in MVP
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    last_login = Column(DateTime, nullable=True)
```

- [ ] **Step 2: Write auth schemas**

```python
# backend/app/schemas/auth.py
from pydantic import BaseModel
from datetime import datetime

class SetupRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool
    created_at: datetime
    last_login: datetime | None

    class Config:
        from_attributes = True

class TokenData(BaseModel):
    user_id: int
    username: str
```

- [ ] **Step 3: Write auth core (JWT + password)**

```python
# backend/app/core/auth.py
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import settings
from app.database import get_db
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_jwt(user_id: int, username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    return jwt.encode(
        {"sub": str(user_id), "username": username, "exp": expire},
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

def decode_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_jwt(token)
    result = await db.execute(select(User).where(User.id == int(payload["sub"])))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
```

- [ ] **Step 4: Write auth tests**

```python
# backend/tests/test_auth.py
import pytest
from app.core.auth import hash_password, verify_password, create_jwt, decode_jwt

def test_password_hash_and_verify():
    hashed = hash_password("testpass123")
    assert verify_password("testpass123", hashed)
    assert not verify_password("wrongpass", hashed)

def test_jwt_create_and_decode():
    token = create_jwt(user_id=1, username="admin")
    payload = decode_jwt(token)
    assert payload["sub"] == "1"
    assert payload["username"] == "admin"

def test_jwt_invalid_token():
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        decode_jwt("invalid.token.here")

@pytest.mark.asyncio
async def test_setup_creates_root_user(client):
    resp = await client.post("/api/auth/setup", json={"username": "root", "password": "rootpass123"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "root"
    assert data["role"] == "root"

@pytest.mark.asyncio
async def test_setup_only_works_once(client):
    await client.post("/api/auth/setup", json={"username": "root", "password": "rootpass123"})
    resp = await client.post("/api/auth/setup", json={"username": "root2", "password": "pass"})
    assert resp.status_code == 400

@pytest.mark.asyncio
async def test_login_success(client):
    await client.post("/api/auth/setup", json={"username": "root", "password": "rootpass123"})
    resp = await client.post("/api/auth/login", json={"username": "root", "password": "rootpass123"})
    assert resp.status_code == 200
    assert "access_token" in resp.cookies

@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/api/auth/setup", json={"username": "root", "password": "rootpass123"})
    resp = await client.post("/api/auth/login", json={"username": "root", "password": "wrong"})
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_me_authenticated(client):
    await client.post("/api/auth/setup", json={"username": "root", "password": "rootpass123"})
    await client.post("/api/auth/login", json={"username": "root", "password": "rootpass123"})
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json()["username"] == "root"

@pytest.mark.asyncio
async def test_me_unauthenticated(client):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401
```

- [ ] **Step 5: Run tests to verify they fail**

Run: `cd /Users/denisgumen/Desktop/code/The-Blackwall/backend && python -m pytest tests/test_auth.py -v`
Expected: FAIL (auth endpoints don't exist yet)

- [ ] **Step 6: Commit model + core + schemas + tests**

```bash
git add backend/app/models/user.py backend/app/core/auth.py backend/app/schemas/auth.py backend/tests/test_auth.py
git commit -m "feat: user model, auth core (JWT+bcrypt), auth schemas and tests"
```

---

## Task 3: Auth API Endpoints + Main App

**Files:**
- Modify: `backend/app/api/auth.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Write auth API endpoints**

```python
# backend/app/api/auth.py
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sa_func
from app.database import get_db
from app.models.user import User
from app.schemas.auth import SetupRequest, LoginRequest, UserResponse
from app.core.auth import hash_password, verify_password, create_jwt, get_current_user
from datetime import datetime, timezone

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Simple in-memory rate limiter for login
_login_attempts: dict[str, list[float]] = {}

def _check_rate_limit(ip: str, max_attempts: int = 5, window: int = 60):
    import time
    now = time.time()
    attempts = _login_attempts.get(ip, [])
    attempts = [t for t in attempts if now - t < window]
    _login_attempts[ip] = attempts
    if len(attempts) >= max_attempts:
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")
    attempts.append(now)
    _login_attempts[ip] = attempts

@router.post("/setup", response_model=UserResponse)
async def setup(req: SetupRequest, db: AsyncSession = Depends(get_db)):
    count = await db.scalar(select(sa_func.count()).select_from(User))
    if count > 0:
        raise HTTPException(status_code=400, detail="Setup already completed")
    user = User(username=req.username, password_hash=hash_password(req.password), role="root")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@router.post("/login")
async def login(req: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    _check_rate_limit(request.client.host if request.client else "unknown")
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user.last_login = datetime.now(timezone.utc)
    await db.commit()
    token = create_jwt(user.id, user.username)
    response.set_cookie("access_token", token, httponly=True, samesite="lax", max_age=86400)
    return {"message": "ok", "user": UserResponse.model_validate(user)}

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "ok"}

@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return user
```

- [ ] **Step 2: Write main.py with lifespan**

```python
# backend/app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="The Blackwall", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.auth import router as auth_router
app.include_router(auth_router)
```

- [ ] **Step 3: Run auth tests — all should pass**

Run: `cd /Users/denisgumen/Desktop/code/The-Blackwall/backend && python -m pytest tests/test_auth.py -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/auth.py backend/app/main.py
git commit -m "feat: auth API endpoints (setup, login, logout, me)"
```

---

## Task 4: System Metrics Core (CPU, RAM, Disk, Traffic)

**Files:**
- Modify: `backend/app/core/metrics.py` (currently stub at `backend/app/core/firewall.py` — we create new file)
- Create: `backend/app/core/metrics.py`
- Modify: `backend/app/schemas/metrics.py` (currently stub)
- Create: `backend/tests/test_metrics.py`

Note: `backend/app/core/` may not have a `metrics.py` yet. The existing `firewall.py` is a stub — leave it. Create `metrics.py` fresh.

- [ ] **Step 1: Write metrics schemas**

```python
# backend/app/schemas/metrics.py
from pydantic import BaseModel

class CpuMetrics(BaseModel):
    usage_percent: float
    cores: int

class MemoryMetrics(BaseModel):
    total_bytes: int
    used_bytes: int
    available_bytes: int
    usage_percent: float

class DiskMetrics(BaseModel):
    total_bytes: int
    used_bytes: int
    free_bytes: int
    usage_percent: float

class SystemMetrics(BaseModel):
    cpu: CpuMetrics
    memory: MemoryMetrics
    disk: DiskMetrics
    uptime_seconds: int
    hostname: str

class InterfaceTraffic(BaseModel):
    name: str
    rx_bytes: int
    tx_bytes: int
    rx_speed: float  # bytes/sec
    tx_speed: float  # bytes/sec
    is_up: bool

class TrafficSnapshot(BaseModel):
    timestamp: float
    interfaces: list[InterfaceTraffic]
```

- [ ] **Step 2: Write metrics core with /proc parsers**

```python
# backend/app/core/metrics.py
import time
import shutil
import socket
from pathlib import Path

_prev_cpu: dict | None = None
_prev_traffic: dict[str, dict] | None = None
_prev_traffic_time: float = 0

def parse_cpu() -> tuple[float, int]:
    """Returns (usage_percent, num_cores). Falls back to 0.0 if /proc/stat unavailable."""
    global _prev_cpu
    try:
        text = Path("/proc/stat").read_text()
    except FileNotFoundError:
        return 0.0, 1
    line = text.splitlines()[0]  # cpu  user nice system idle iowait irq softirq
    parts = line.split()[1:]
    vals = [int(v) for v in parts]
    idle = vals[3] + vals[4]
    total = sum(vals)
    cores = sum(1 for l in text.splitlines() if l.startswith("cpu") and l[3:4].isdigit())
    if _prev_cpu is None:
        _prev_cpu = {"idle": idle, "total": total}
        return 0.0, cores
    d_idle = idle - _prev_cpu["idle"]
    d_total = total - _prev_cpu["total"]
    _prev_cpu = {"idle": idle, "total": total}
    if d_total == 0:
        return 0.0, cores
    return round((1 - d_idle / d_total) * 100, 1), cores

def parse_memory() -> dict:
    """Returns dict with total, used, available, percent."""
    try:
        text = Path("/proc/meminfo").read_text()
    except FileNotFoundError:
        return {"total": 0, "used": 0, "available": 0, "percent": 0.0}
    info = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            info[parts[0].rstrip(":")] = int(parts[1]) * 1024  # kB -> bytes
    total = info.get("MemTotal", 0)
    available = info.get("MemAvailable", 0)
    used = total - available
    pct = round(used / total * 100, 1) if total > 0 else 0.0
    return {"total": total, "used": used, "available": available, "percent": pct}

def parse_disk() -> dict:
    usage = shutil.disk_usage("/")
    pct = round(usage.used / usage.total * 100, 1) if usage.total > 0 else 0.0
    return {"total": usage.total, "used": usage.used, "free": usage.free, "percent": pct}

def get_uptime() -> int:
    try:
        text = Path("/proc/uptime").read_text()
        return int(float(text.split()[0]))
    except FileNotFoundError:
        return 0

def get_hostname() -> str:
    return socket.gethostname()

def parse_traffic() -> list[dict]:
    """Returns list of interface traffic dicts with speed calculation."""
    global _prev_traffic, _prev_traffic_time
    now = time.time()
    try:
        text = Path("/proc/net/dev").read_text()
    except FileNotFoundError:
        return []
    result = []
    for line in text.splitlines()[2:]:  # skip headers
        parts = line.split()
        if not parts:
            continue
        name = parts[0].rstrip(":")
        if name == "lo":
            continue
        rx_bytes = int(parts[1])
        tx_bytes = int(parts[9])
        rx_speed = 0.0
        tx_speed = 0.0
        if _prev_traffic and name in _prev_traffic:
            dt = now - _prev_traffic_time
            if dt > 0:
                rx_speed = (rx_bytes - _prev_traffic[name]["rx"]) / dt
                tx_speed = (tx_bytes - _prev_traffic[name]["tx"]) / dt
        result.append({
            "name": name,
            "rx_bytes": rx_bytes,
            "tx_bytes": tx_bytes,
            "rx_speed": round(max(0, rx_speed), 1),
            "tx_speed": round(max(0, tx_speed), 1),
            "is_up": True,
        })
    _prev_traffic = {r["name"]: {"rx": r["rx_bytes"], "tx": r["tx_bytes"]} for r in result}
    _prev_traffic_time = now
    return result

def get_system_metrics() -> dict:
    cpu_pct, cores = parse_cpu()
    mem = parse_memory()
    disk = parse_disk()
    return {
        "cpu": {"usage_percent": cpu_pct, "cores": cores},
        "memory": {"total_bytes": mem["total"], "used_bytes": mem["used"], "available_bytes": mem["available"], "usage_percent": mem["percent"]},
        "disk": {"total_bytes": disk["total"], "used_bytes": disk["used"], "free_bytes": disk["free"], "usage_percent": disk["percent"]},
        "uptime_seconds": get_uptime(),
        "hostname": get_hostname(),
    }
```

- [ ] **Step 3: Write metrics tests (mocking /proc)**

```python
# backend/tests/test_metrics.py
from unittest.mock import patch, mock_open
from app.core import metrics

PROC_STAT = """cpu  10132153 290696 3084719 46828483 16683 0 25195 0 0 0
cpu0 5066076 145348 1542359 23414241 8341 0 12597 0 0 0
cpu1 5066077 145348 1542360 23414242 8342 0 12598 0 0 0
"""

PROC_MEMINFO = """MemTotal:       16384000 kB
MemFree:         2048000 kB
MemAvailable:    8192000 kB
Buffers:          512000 kB
Cached:          4096000 kB
"""

PROC_NET_DEV = """Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
    lo: 1000000  10000    0    0    0     0          0         0  1000000  10000    0    0    0     0       0          0
  eth0: 5000000  50000    0    0    0     0          0         0  3000000  30000    0    0    0     0       0          0
  eth1: 2000000  20000    0    0    0     0          0         0  1000000  10000    0    0    0     0       0          0
"""

def test_parse_memory():
    with patch("pathlib.Path.read_text", return_value=PROC_MEMINFO):
        mem = metrics.parse_memory()
        assert mem["total"] == 16384000 * 1024
        assert mem["available"] == 8192000 * 1024
        assert mem["used"] == mem["total"] - mem["available"]
        assert 0 < mem["percent"] < 100

def test_parse_cpu():
    metrics._prev_cpu = None
    with patch("pathlib.Path.read_text", return_value=PROC_STAT):
        pct, cores = metrics.parse_cpu()
        assert cores == 2
        # First call returns 0.0 (no previous data)
        assert pct == 0.0

def test_parse_traffic():
    metrics._prev_traffic = None
    metrics._prev_traffic_time = 0
    with patch("pathlib.Path.read_text", return_value=PROC_NET_DEV):
        result = metrics.parse_traffic()
        assert len(result) == 2  # lo excluded
        assert result[0]["name"] == "eth0"
        assert result[0]["rx_bytes"] == 5000000
        assert result[1]["name"] == "eth1"

def test_parse_disk():
    disk = metrics.parse_disk()
    assert disk["total"] > 0
    assert 0 <= disk["percent"] <= 100

def test_get_system_metrics_on_macos():
    """On macOS (dev), /proc doesn't exist — should return zeros gracefully."""
    m = metrics.get_system_metrics()
    assert "cpu" in m
    assert "memory" in m
    assert "disk" in m
    assert "hostname" in m
```

- [ ] **Step 4: Run tests**

Run: `cd /Users/denisgumen/Desktop/code/The-Blackwall/backend && python -m pytest tests/test_metrics.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/metrics.py backend/app/schemas/metrics.py backend/tests/test_metrics.py
git commit -m "feat: system metrics parsing (CPU, RAM, disk, traffic from /proc)"
```

---

## Task 5: Metrics API + WebSocket

**Files:**
- Modify: `backend/app/api/metrics.py` (currently stub)
- Modify: `backend/app/main.py`

- [ ] **Step 1: Write metrics API with REST + WebSocket**

```python
# backend/app/api/metrics.py
import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.core.auth import get_current_user
from app.core.metrics import get_system_metrics, parse_traffic
from app.models.user import User
from app.core.auth import decode_jwt

router = APIRouter(prefix="/api", tags=["metrics"])

@router.get("/metrics/system")
async def system_metrics(user: User = Depends(get_current_user)):
    return get_system_metrics()

@router.websocket("/ws/traffic")
async def traffic_ws(ws: WebSocket):
    # Auth via cookie
    token = ws.cookies.get("access_token")
    if not token:
        await ws.close(code=4001)
        return
    try:
        decode_jwt(token)
    except Exception:
        await ws.close(code=4001)
        return
    await ws.accept()
    try:
        while True:
            data = parse_traffic()
            await ws.send_json({"interfaces": data, "timestamp": __import__("time").time()})
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
```

- [ ] **Step 2: Register metrics router in main.py**

Add to `backend/app/main.py` after the auth router import:

```python
from app.api.metrics import router as metrics_router
app.include_router(metrics_router)
```

- [ ] **Step 3: Run all tests**

Run: `cd /Users/denisgumen/Desktop/code/The-Blackwall/backend && python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/metrics.py backend/app/main.py
git commit -m "feat: metrics REST + WebSocket endpoints"
```

---

## Task 6: Load Balancer Models + Schemas

**Files:**
- Create: `backend/app/models/loadbalancer.py`
- Create: `backend/app/schemas/loadbalancer.py`

- [ ] **Step 0: Update models/__init__.py to import LB models**

```python
# backend/app/models/__init__.py
from app.models.user import User
from app.models.loadbalancer import LBConfig, LBProvider
```

- [ ] **Step 1: Write LB models**

```python
# backend/app/models/loadbalancer.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from app.database import Base

class LBConfig(Base):
    __tablename__ = "lb_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mode = Column(String(20), nullable=False, default="failover")  # round-robin | failover
    check_interval = Column(Integer, nullable=False, default=2)
    check_timeout = Column(Integer, nullable=False, default=1000)  # ms
    check_target = Column(String(50), nullable=False, default="8.8.8.8")
    is_enabled = Column(Boolean, default=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class LBProvider(Base):
    __tablename__ = "lb_providers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    gateway_ip = Column(String(45), nullable=False)
    interface = Column(String(20), nullable=False)
    weight = Column(Integer, nullable=False, default=50)
    priority = Column(Integer, nullable=False, default=1)  # 1=primary, 2=backup
    is_active = Column(Boolean, default=True)
    is_healthy = Column(Boolean, default=True)
    last_check = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
```

- [ ] **Step 2: Write LB schemas**

```python
# backend/app/schemas/loadbalancer.py
from pydantic import BaseModel, field_validator
from datetime import datetime
import ipaddress

class LBConfigUpdate(BaseModel):
    mode: str = "failover"
    check_interval: int = 2
    check_timeout: int = 1000
    check_target: str = "8.8.8.8"
    is_enabled: bool = False

    @field_validator("mode")
    @classmethod
    def valid_mode(cls, v):
        if v not in ("round-robin", "failover"):
            raise ValueError("mode must be round-robin or failover")
        return v

class LBConfigResponse(BaseModel):
    id: int
    mode: str
    check_interval: int
    check_timeout: int
    check_target: str
    is_enabled: bool
    updated_at: datetime | None

    class Config:
        from_attributes = True

class LBProviderCreate(BaseModel):
    name: str
    gateway_ip: str
    interface: str
    weight: int = 50
    priority: int = 1

    @field_validator("gateway_ip")
    @classmethod
    def valid_ip(cls, v):
        ipaddress.ip_address(v)
        return v

class LBProviderUpdate(BaseModel):
    name: str | None = None
    gateway_ip: str | None = None
    interface: str | None = None
    weight: int | None = None
    priority: int | None = None
    is_active: bool | None = None

class LBProviderResponse(BaseModel):
    id: int
    name: str
    gateway_ip: str
    interface: str
    weight: int
    priority: int
    is_active: bool
    is_healthy: bool
    last_check: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True

class LBStatusResponse(BaseModel):
    config: LBConfigResponse
    providers: list[LBProviderResponse]
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/loadbalancer.py backend/app/schemas/loadbalancer.py
git commit -m "feat: load balancer models and schemas"
```

---

## Task 7: Load Balancer Engine (ip route/rule management)

**Files:**
- Create: `backend/app/core/lb_engine.py`
- Create: `backend/tests/test_lb_engine.py`

- [ ] **Step 1: Write LB engine tests first**

```python
# backend/tests/test_lb_engine.py
from unittest.mock import patch, AsyncMock
import pytest
from app.core.lb_engine import LBEngine

@pytest.fixture
def engine():
    return LBEngine()

@pytest.mark.asyncio
async def test_build_multipath_command(engine):
    providers = [
        {"gateway_ip": "192.168.1.1", "interface": "eth0", "weight": 50},
        {"gateway_ip": "10.0.0.1", "interface": "eth1", "weight": 50},
    ]
    cmd = engine.build_multipath_cmd(providers)
    assert "nexthop" in cmd
    assert "192.168.1.1" in cmd
    assert "10.0.0.1" in cmd

@pytest.mark.asyncio
async def test_build_failover_command(engine):
    cmd = engine.build_failover_cmd("192.168.1.1", "eth0")
    assert "ip route replace default" in cmd
    assert "192.168.1.1" in cmd

@pytest.mark.asyncio
async def test_apply_round_robin(engine):
    providers = [
        {"gateway_ip": "192.168.1.1", "interface": "eth0", "weight": 50},
        {"gateway_ip": "10.0.0.1", "interface": "eth1", "weight": 50},
    ]
    with patch("asyncio.create_subprocess_shell", new_callable=AsyncMock) as mock_proc:
        mock_proc.return_value.communicate = AsyncMock(return_value=(b"", b""))
        mock_proc.return_value.returncode = 0
        result = await engine.apply_round_robin(providers)
        assert result is True

@pytest.mark.asyncio
async def test_apply_failover(engine):
    with patch("asyncio.create_subprocess_shell", new_callable=AsyncMock) as mock_proc:
        mock_proc.return_value.communicate = AsyncMock(return_value=(b"", b""))
        mock_proc.return_value.returncode = 0
        result = await engine.apply_failover("192.168.1.1", "eth0")
        assert result is True

@pytest.mark.asyncio
async def test_clear_routes(engine):
    with patch("asyncio.create_subprocess_shell", new_callable=AsyncMock) as mock_proc:
        mock_proc.return_value.communicate = AsyncMock(return_value=(b"", b""))
        mock_proc.return_value.returncode = 0
        await engine.clear_routes()
        mock_proc.assert_called()
```

- [ ] **Step 2: Write LB engine implementation**

```python
# backend/app/core/lb_engine.py
import asyncio
import logging

logger = logging.getLogger(__name__)

class LBEngine:
    async def _run(self, cmd: str) -> tuple[bool, str]:
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        ok = proc.returncode == 0
        if not ok:
            logger.error(f"Command failed: {cmd} — {stderr.decode()}")
        return ok, stderr.decode()

    def build_multipath_cmd(self, providers: list[dict]) -> str:
        parts = ["ip route replace default"]
        for p in providers:
            parts.append(f"nexthop via {p['gateway_ip']} dev {p['interface']} weight {p['weight']}")
        return " ".join(parts)

    def build_failover_cmd(self, gateway_ip: str, interface: str) -> str:
        return f"ip route replace default via {gateway_ip} dev {interface}"

    async def apply_round_robin(self, providers: list[dict]) -> bool:
        cmd = self.build_multipath_cmd(providers)
        ok, _ = await self._run(cmd)
        return ok

    async def apply_failover(self, gateway_ip: str, interface: str) -> bool:
        cmd = self.build_failover_cmd(gateway_ip, interface)
        ok, _ = await self._run(cmd)
        return ok

    async def clear_routes(self) -> bool:
        ok, _ = await self._run("ip route del default 2>/dev/null; true")
        return ok

lb_engine = LBEngine()
```

- [ ] **Step 3: Run tests**

Run: `cd /Users/denisgumen/Desktop/code/The-Blackwall/backend && python -m pytest tests/test_lb_engine.py -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/core/lb_engine.py backend/tests/test_lb_engine.py
git commit -m "feat: load balancer engine (ip route/rule management)"
```

---

## Task 8: Health Monitor (Background Ping)

**Files:**
- Create: `backend/app/core/lb_monitor.py`
- Create: `backend/tests/test_lb_monitor.py`

- [ ] **Step 1: Write monitor tests**

```python
# backend/tests/test_lb_monitor.py
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.core.lb_monitor import HealthMonitor

@pytest.mark.asyncio
async def test_ping_success():
    monitor = HealthMonitor()
    with patch("asyncio.create_subprocess_shell", new_callable=AsyncMock) as mock_proc:
        mock_proc.return_value.communicate = AsyncMock(return_value=(b"", b""))
        mock_proc.return_value.returncode = 0
        result = await monitor.ping("8.8.8.8", "eth0", timeout_ms=1000)
        assert result is True

@pytest.mark.asyncio
async def test_ping_failure():
    monitor = HealthMonitor()
    with patch("asyncio.create_subprocess_shell", new_callable=AsyncMock) as mock_proc:
        mock_proc.return_value.communicate = AsyncMock(return_value=(b"", b"timeout"))
        mock_proc.return_value.returncode = 1
        result = await monitor.ping("8.8.8.8", "eth0", timeout_ms=1000)
        assert result is False

def test_health_state_tracking():
    monitor = HealthMonitor()
    # 3 failures → unhealthy
    for _ in range(3):
        monitor.record_result(1, False)
    assert monitor.is_healthy(1) is False

    # 2 successes → healthy again
    monitor.record_result(1, True)
    monitor.record_result(1, True)
    assert monitor.is_healthy(1) is True
```

- [ ] **Step 2: Write health monitor**

```python
# backend/app/core/lb_monitor.py
import asyncio
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

class HealthMonitor:
    def __init__(self):
        self._fail_counts: dict[int, int] = defaultdict(int)
        self._success_counts: dict[int, int] = defaultdict(int)
        self._healthy: dict[int, bool] = {}
        self._task: asyncio.Task | None = None
        self._callbacks: list = []

    async def ping(self, target: str, interface: str, timeout_ms: int = 1000) -> bool:
        timeout_s = timeout_ms / 1000
        cmd = f"ping -c 1 -W {int(timeout_s)} -I {interface} {target} 2>/dev/null"
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(proc.communicate(), timeout=timeout_s + 2)
            return proc.returncode == 0
        except (asyncio.TimeoutError, Exception):
            return False

    def record_result(self, provider_id: int, success: bool):
        if success:
            self._success_counts[provider_id] += 1
            self._fail_counts[provider_id] = 0
            if self._success_counts[provider_id] >= 2:
                self._healthy[provider_id] = True
        else:
            self._fail_counts[provider_id] += 1
            self._success_counts[provider_id] = 0
            if self._fail_counts[provider_id] >= 3:
                self._healthy[provider_id] = False

    def is_healthy(self, provider_id: int) -> bool:
        return self._healthy.get(provider_id, True)

    def on_status_change(self, callback):
        self._callbacks.append(callback)

    async def start(self, get_config_fn, get_providers_fn, on_failover_fn):
        """Main monitoring loop. get_config_fn and get_providers_fn are async callables."""
        self._task = asyncio.current_task()
        while True:
            try:
                config = await get_config_fn()
                if not config or not config.is_enabled:
                    await asyncio.sleep(5)
                    continue
                providers = await get_providers_fn()
                for p in providers:
                    if not p.is_active:
                        continue
                    ok = await self.ping(config.check_target, p.interface, config.check_timeout)
                    was_healthy = self.is_healthy(p.id)
                    self.record_result(p.id, ok)
                    now_healthy = self.is_healthy(p.id)
                    if was_healthy != now_healthy:
                        logger.warning(f"Provider {p.name} ({p.gateway_ip}): {'UP' if now_healthy else 'DOWN'}")
                        await on_failover_fn(p.id, now_healthy)
                interval = 1 if config.mode == "failover" else config.check_interval
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(5)

    def stop(self):
        if self._task:
            self._task.cancel()

health_monitor = HealthMonitor()
```

- [ ] **Step 3: Run tests**

Run: `cd /Users/denisgumen/Desktop/code/The-Blackwall/backend && python -m pytest tests/test_lb_monitor.py -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/core/lb_monitor.py backend/tests/test_lb_monitor.py
git commit -m "feat: health monitor with ping-based gateway checking"
```

---

## Task 9: Load Balancer API Endpoints

**Files:**
- Modify: `backend/app/api/loadbalancer.py` (currently stub)
- Create: `backend/tests/test_lb_api.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Write LB API tests**

```python
# backend/tests/test_lb_api.py
import pytest

async def auth_client(client):
    """Helper: setup + login, return authenticated client."""
    await client.post("/api/auth/setup", json={"username": "root", "password": "rootpass123"})
    await client.post("/api/auth/login", json={"username": "root", "password": "rootpass123"})
    return client

@pytest.mark.asyncio
async def test_get_config_default(client):
    c = await auth_client(client)
    resp = await c.get("/api/lb/config")
    assert resp.status_code == 200
    assert resp.json()["mode"] == "failover"

@pytest.mark.asyncio
async def test_update_config(client):
    c = await auth_client(client)
    resp = await c.put("/api/lb/config", json={"mode": "round-robin", "is_enabled": False})
    assert resp.status_code == 200
    assert resp.json()["mode"] == "round-robin"

@pytest.mark.asyncio
async def test_add_provider(client):
    c = await auth_client(client)
    resp = await c.post("/api/lb/providers", json={
        "name": "ISP1", "gateway_ip": "192.168.1.1", "interface": "eth0", "weight": 50, "priority": 1
    })
    assert resp.status_code == 200
    assert resp.json()["name"] == "ISP1"

@pytest.mark.asyncio
async def test_list_providers(client):
    c = await auth_client(client)
    await c.post("/api/lb/providers", json={
        "name": "ISP1", "gateway_ip": "192.168.1.1", "interface": "eth0"
    })
    resp = await c.get("/api/lb/providers")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

@pytest.mark.asyncio
async def test_delete_last_provider_blocked(client):
    c = await auth_client(client)
    resp = await c.post("/api/lb/providers", json={
        "name": "ISP1", "gateway_ip": "192.168.1.1", "interface": "eth0"
    })
    pid = resp.json()["id"]
    # Enable LB first
    await c.put("/api/lb/config", json={"is_enabled": True})
    # Try to delete the only provider — should fail
    resp = await c.delete(f"/api/lb/providers/{pid}")
    assert resp.status_code == 400

@pytest.mark.asyncio
async def test_get_status(client):
    c = await auth_client(client)
    resp = await c.get("/api/lb/status")
    assert resp.status_code == 200
    assert "config" in resp.json()
    assert "providers" in resp.json()
```

- [ ] **Step 2: Write LB API endpoints**

```python
# backend/app/api/loadbalancer.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sa_func
from app.database import get_db
from app.models.user import User
from app.models.loadbalancer import LBConfig, LBProvider
from app.schemas.loadbalancer import (
    LBConfigUpdate, LBConfigResponse,
    LBProviderCreate, LBProviderUpdate, LBProviderResponse,
    LBStatusResponse,
)
from app.core.auth import get_current_user

router = APIRouter(prefix="/api/lb", tags=["loadbalancer"])

async def _get_or_create_config(db: AsyncSession) -> LBConfig:
    result = await db.execute(select(LBConfig))
    config = result.scalar_one_or_none()
    if not config:
        config = LBConfig()
        db.add(config)
        await db.commit()
        await db.refresh(config)
    return config

@router.get("/config", response_model=LBConfigResponse)
async def get_config(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return await _get_or_create_config(db)

@router.put("/config", response_model=LBConfigResponse)
async def update_config(data: LBConfigUpdate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    config = await _get_or_create_config(db)
    for key, val in data.model_dump().items():
        setattr(config, key, val)
    await db.commit()
    await db.refresh(config)
    return config

@router.get("/providers", response_model=list[LBProviderResponse])
async def list_providers(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(LBProvider).order_by(LBProvider.priority))
    return result.scalars().all()

@router.post("/providers", response_model=LBProviderResponse)
async def add_provider(data: LBProviderCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    provider = LBProvider(**data.model_dump())
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    return provider

@router.put("/providers/{provider_id}", response_model=LBProviderResponse)
async def update_provider(provider_id: int, data: LBProviderUpdate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(LBProvider).where(LBProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(provider, key, val)
    await db.commit()
    await db.refresh(provider)
    return provider

@router.delete("/providers/{provider_id}")
async def delete_provider(provider_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    config = await _get_or_create_config(db)
    if config.is_enabled:
        count = await db.scalar(select(sa_func.count()).select_from(LBProvider).where(LBProvider.is_active == True))
        if count <= 1:
            raise HTTPException(status_code=400, detail="Cannot delete last active provider while LB is enabled")
    result = await db.execute(select(LBProvider).where(LBProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    await db.delete(provider)
    await db.commit()
    return {"message": "deleted"}

@router.get("/status", response_model=LBStatusResponse)
async def get_status(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    config = await _get_or_create_config(db)
    result = await db.execute(select(LBProvider).order_by(LBProvider.priority))
    providers = result.scalars().all()
    return {"config": config, "providers": providers}
```

- [ ] **Step 3: Register LB router in main.py**

Add to `backend/app/main.py`:

```python
from app.api.loadbalancer import router as lb_router
app.include_router(lb_router)
```

- [ ] **Step 4: Run all backend tests**

Run: `cd /Users/denisgumen/Desktop/code/The-Blackwall/backend && python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/loadbalancer.py backend/tests/test_lb_api.py backend/app/main.py
git commit -m "feat: load balancer API endpoints with tests"
```

---

## Task 10: Frontend Setup — Package.json, Vite, Tailwind

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/vite.config.ts`
- Modify: `frontend/tailwind.config.js`
- Create: `frontend/postcss.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/index.css`
- Modify: `frontend/tsconfig.json`

- [ ] **Step 1: Write package.json**

```json
{
  "name": "the-blackwall",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "recharts": "^2.10.0",
    "lucide-react": "^0.294.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.2.0",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.32",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0"
  }
}
```

- [ ] **Step 2: Write vite.config.ts**

```typescript
// frontend/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': { target: 'ws://localhost:8000', ws: true },
    },
  },
})
```

- [ ] **Step 3: Write tailwind.config.js**

```javascript
// frontend/tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        dark: {
          900: '#0f1117',
          800: '#1a1d27',
          700: '#252832',
          600: '#2f3340',
        },
        accent: {
          DEFAULT: '#06b6d4',
          light: '#22d3ee',
          dark: '#0891b2',
        },
      },
    },
  },
  plugins: [],
}
```

- [ ] **Step 4: Write postcss.config.js**

```javascript
// frontend/postcss.config.js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

- [ ] **Step 5: Write index.html**

```html
<!-- frontend/index.html -->
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>The Blackwall</title>
  <link rel="icon" href="/favicon.ico" />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
</head>
<body class="bg-dark-900 text-gray-100 font-['Inter',sans-serif]">
  <div id="root"></div>
  <script type="module" src="/src/main.tsx"></script>
</body>
</html>
```

- [ ] **Step 6: Write index.css**

```css
/* frontend/src/index.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

* {
  scrollbar-width: thin;
  scrollbar-color: #2f3340 #0f1117;
}
```

- [ ] **Step 7: Write tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": false,
    "noUnusedParameters": false
  },
  "include": ["src"]
}
```

- [ ] **Step 8: Install dependencies**

Run: `cd /Users/denisgumen/Desktop/code/The-Blackwall/frontend && npm install`

- [ ] **Step 9: Commit**

```bash
git add frontend/
git commit -m "feat: frontend setup (Vite, React, Tailwind, Recharts)"
```

---

## Task 11: Frontend — Types, API Client, Auth Hook

**Files:**
- Modify: `frontend/src/types/index.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/hooks/useAuth.ts`
- Create: `frontend/src/hooks/useWebSocket.ts`

- [ ] **Step 1: Write TypeScript types**

```typescript
// frontend/src/types/index.ts
export interface User {
  id: number
  username: string
  role: string
  is_active: boolean
  created_at: string
  last_login: string | null
}

export interface SystemMetrics {
  cpu: { usage_percent: number; cores: number }
  memory: { total_bytes: number; used_bytes: number; available_bytes: number; usage_percent: number }
  disk: { total_bytes: number; used_bytes: number; free_bytes: number; usage_percent: number }
  uptime_seconds: number
  hostname: string
}

export interface InterfaceTraffic {
  name: string
  rx_bytes: number
  tx_bytes: number
  rx_speed: number
  tx_speed: number
  is_up: boolean
}

export interface TrafficSnapshot {
  timestamp: number
  interfaces: InterfaceTraffic[]
}

export interface LBConfig {
  id: number
  mode: 'round-robin' | 'failover'
  check_interval: number
  check_timeout: number
  check_target: string
  is_enabled: boolean
  updated_at: string | null
}

export interface LBProvider {
  id: number
  name: string
  gateway_ip: string
  interface: string
  weight: number
  priority: number
  is_active: boolean
  is_healthy: boolean
  last_check: string | null
  created_at: string
}
```

- [ ] **Step 2: Write API client**

```typescript
// frontend/src/api/client.ts
const BASE = ''

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${url}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (resp.status === 401) {
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }))
    throw new Error(err.detail || resp.statusText)
  }
  return resp.json()
}

export const api = {
  get: <T>(url: string) => request<T>(url),
  post: <T>(url: string, body?: unknown) => request<T>(url, { method: 'POST', body: body ? JSON.stringify(body) : undefined }),
  put: <T>(url: string, body?: unknown) => request<T>(url, { method: 'PUT', body: body ? JSON.stringify(body) : undefined }),
  del: <T>(url: string) => request<T>(url, { method: 'DELETE' }),
}
```

- [ ] **Step 3: Write useAuth hook**

```typescript
// frontend/src/hooks/useAuth.ts
import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'
import type { User } from '../types'

export function useAuth() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [needsSetup, setNeedsSetup] = useState(false)

  const checkAuth = useCallback(async () => {
    try {
      const u = await api.get<User>('/api/auth/me')
      setUser(u)
    } catch {
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { checkAuth() }, [checkAuth])

  const login = async (username: string, password: string) => {
    const resp = await api.post<{ user: User }>('/api/auth/login', { username, password })
    setUser(resp.user)
  }

  const setup = async (username: string, password: string) => {
    await api.post<User>('/api/auth/setup', { username, password })
    await login(username, password)
  }

  const logout = async () => {
    await api.post('/api/auth/logout')
    setUser(null)
  }

  return { user, loading, needsSetup, setNeedsSetup, login, setup, logout }
}
```

- [ ] **Step 4: Write useWebSocket hook**

```typescript
// frontend/src/hooks/useWebSocket.ts
import { useEffect, useRef, useState, useCallback } from 'react'

export function useWebSocket<T>(url: string, enabled: boolean = true) {
  const [data, setData] = useState<T | null>(null)
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectRef = useRef<ReturnType<typeof setTimeout>>()

  const connect = useCallback(() => {
    if (!enabled) return
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${window.location.host}${url}`)
    wsRef.current = ws

    ws.onopen = () => setConnected(true)
    ws.onclose = () => {
      setConnected(false)
      reconnectRef.current = setTimeout(connect, 3000)
    }
    ws.onmessage = (e) => {
      try { setData(JSON.parse(e.data)) } catch {}
    }
  }, [url, enabled])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectRef.current)
      wsRef.current?.close()
    }
  }, [connect])

  return { data, connected }
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/client.ts frontend/src/hooks/useAuth.ts frontend/src/hooks/useWebSocket.ts
git commit -m "feat: frontend types, API client, auth and WebSocket hooks"
```

---

## Task 12: Frontend — Login Page

**Files:**
- Create: `frontend/src/pages/LoginPage.tsx`
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Write LoginPage**

```tsx
// frontend/src/pages/LoginPage.tsx
import { useState, FormEvent } from 'react'
import { useAuth } from '../hooks/useAuth'

export default function LoginPage() {
  const { login, setup, needsSetup, setNeedsSetup } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isSetup, setIsSetup] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      if (isSetup) {
        await setup(username, password)
      } else {
        await login(username, password)
      }
    } catch (err: any) {
      setError(err.message || 'Authentication failed')
      if (err.message?.includes('Setup')) {
        setIsSetup(true)
        setNeedsSetup(true)
      }
    }
  }

  return (
    <div className="min-h-screen bg-dark-900 flex items-center justify-center">
      <div className="bg-dark-800 border border-dark-600 rounded-xl p-8 w-full max-w-sm shadow-2xl">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-accent">The Blackwall</h1>
          <p className="text-gray-500 text-sm mt-1">
            {isSetup ? 'Initial Setup — Create Root Account' : 'Firewall Management System'}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider">Username</label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2.5 text-sm text-gray-100 focus:outline-none focus:border-accent transition"
              required
              autoFocus
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1 uppercase tracking-wider">Password</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2.5 text-sm text-gray-100 focus:outline-none focus:border-accent transition"
              required
            />
          </div>

          {error && (
            <p className="text-red-400 text-sm bg-red-400/10 rounded-lg px-3 py-2">{error}</p>
          )}

          <button
            type="submit"
            className="w-full bg-accent hover:bg-accent-light text-dark-900 font-semibold rounded-lg py-2.5 text-sm transition"
          >
            {isSetup ? 'Create Account' : 'Sign In'}
          </button>
        </form>

        {!isSetup && (
          <button
            onClick={() => setIsSetup(true)}
            className="w-full mt-3 text-xs text-gray-500 hover:text-gray-300 transition"
          >
            First time? Create root account
          </button>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Write main.tsx**

```tsx
// frontend/src/main.tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
)
```

- [ ] **Step 3: Write App.tsx with routes**

```tsx
// frontend/src/App.tsx
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './hooks/useAuth'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import LoadBalancerPage from './pages/LoadBalancerPage'
import Layout from './components/Layout'

export default function App() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen bg-dark-900 flex items-center justify-center">
        <div className="text-accent animate-pulse text-lg">Loading...</div>
      </div>
    )
  }

  if (!user) {
    return <LoginPage />
  }

  return (
    <Layout user={user}>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/loadbalancer" element={<LoadBalancerPage />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </Layout>
  )
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/main.tsx frontend/src/App.tsx frontend/src/pages/LoginPage.tsx frontend/src/index.css
git commit -m "feat: login page, app routing, entry point"
```

---

## Task 13: Frontend — Layout Component (Sidebar Nav)

**Files:**
- Create: `frontend/src/components/Layout.tsx`

- [ ] **Step 1: Write Layout component**

```tsx
// frontend/src/components/Layout.tsx
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import type { User } from '../types'

const nav = [
  { path: '/', label: 'Dashboard', icon: '⊞' },
  { path: '/loadbalancer', label: 'Load Balancer', icon: '⇄' },
]

export default function Layout({ user, children }: { user: User; children: React.ReactNode }) {
  const location = useLocation()
  const { logout } = useAuth()

  return (
    <div className="min-h-screen bg-dark-900 flex">
      {/* Sidebar */}
      <aside className="w-56 bg-dark-800 border-r border-dark-600 flex flex-col">
        <div className="p-4 border-b border-dark-600">
          <h1 className="text-lg font-bold text-accent">The Blackwall</h1>
        </div>
        <nav className="flex-1 p-2 space-y-1">
          {nav.map(item => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition ${
                location.pathname === item.path
                  ? 'bg-accent/10 text-accent'
                  : 'text-gray-400 hover:bg-dark-700 hover:text-gray-200'
              }`}
            >
              <span className="text-base">{item.icon}</span>
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="p-3 border-t border-dark-600">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500">{user.username}</span>
            <button
              onClick={logout}
              className="text-xs text-gray-500 hover:text-red-400 transition"
            >
              Logout
            </button>
          </div>
        </div>
      </aside>
      {/* Main content */}
      <main className="flex-1 p-6 overflow-auto">
        {children}
      </main>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Layout.tsx
git commit -m "feat: sidebar layout component"
```

---

## Task 14: Frontend — Dashboard Page (ServerLoad, TrafficChart, InterfaceList)

**Files:**
- Create: `frontend/src/components/ServerLoad.tsx`
- Create: `frontend/src/components/TrafficChart.tsx`
- Create: `frontend/src/components/InterfaceList.tsx`
- Create: `frontend/src/pages/DashboardPage.tsx`

- [ ] **Step 1: Write ServerLoad component**

```tsx
// frontend/src/components/ServerLoad.tsx
import type { SystemMetrics } from '../types'

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`
}

function formatUptime(seconds: number): string {
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  return `${d}d ${h}h ${m}m`
}

function Bar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-gray-400">{label}</span>
        <span className="text-gray-300 font-medium">{value.toFixed(1)}%</span>
      </div>
      <div className="h-2 bg-dark-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-500 ${color}`} style={{ width: `${Math.min(value, 100)}%` }} />
      </div>
    </div>
  )
}

export default function ServerLoad({ metrics }: { metrics: SystemMetrics | null }) {
  if (!metrics) return <div className="text-gray-500 text-sm">Loading metrics...</div>

  return (
    <div className="bg-dark-800 border border-dark-600 rounded-xl p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-300">Server Load</h2>
        <span className="text-xs text-gray-500">{metrics.hostname}</span>
      </div>
      <Bar label="CPU" value={metrics.cpu.usage_percent} color="bg-accent" />
      <Bar label="RAM" value={metrics.memory.usage_percent} color="bg-emerald-500" />
      <Bar label="Disk" value={metrics.disk.usage_percent} color="bg-amber-500" />
      <div className="flex justify-between text-xs text-gray-500 pt-1 border-t border-dark-600">
        <span>RAM: {formatBytes(metrics.memory.used_bytes)} / {formatBytes(metrics.memory.total_bytes)}</span>
        <span>Uptime: {formatUptime(metrics.uptime_seconds)}</span>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Write TrafficChart component**

```tsx
// frontend/src/components/TrafficChart.tsx
import { useMemo } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import type { TrafficSnapshot } from '../types'

function formatSpeed(bytesPerSec: number): string {
  if (bytesPerSec < 1024) return `${bytesPerSec.toFixed(0)} B/s`
  if (bytesPerSec < 1024 * 1024) return `${(bytesPerSec / 1024).toFixed(1)} KB/s`
  if (bytesPerSec < 1024 * 1024 * 1024) return `${(bytesPerSec / (1024 * 1024)).toFixed(1)} MB/s`
  return `${(bytesPerSec / (1024 * 1024 * 1024)).toFixed(2)} GB/s`
}

const COLORS = ['#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']

interface Props {
  history: TrafficSnapshot[]
}

export default function TrafficChart({ history }: Props) {
  const { chartData, interfaces } = useMemo(() => {
    if (!history.length) return { chartData: [], interfaces: [] }
    const ifaces = history[0]?.interfaces.map(i => i.name) || []
    const data = history.map(snap => {
      const point: Record<string, number | string> = {
        time: new Date(snap.timestamp * 1000).toLocaleTimeString(),
      }
      snap.interfaces.forEach(iface => {
        point[`${iface.name}_rx`] = iface.rx_speed
        point[`${iface.name}_tx`] = iface.tx_speed
      })
      return point
    })
    return { chartData: data, interfaces: ifaces }
  }, [history])

  if (!chartData.length) {
    return (
      <div className="bg-dark-800 border border-dark-600 rounded-xl p-4 h-64 flex items-center justify-center text-gray-500 text-sm">
        Waiting for traffic data...
      </div>
    )
  }

  return (
    <div className="bg-dark-800 border border-dark-600 rounded-xl p-4">
      <h2 className="text-sm font-semibold text-gray-300 mb-3">Network Traffic</h2>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={chartData}>
          <XAxis dataKey="time" tick={{ fontSize: 10, fill: '#6b7280' }} interval="preserveStartEnd" />
          <YAxis tick={{ fontSize: 10, fill: '#6b7280' }} tickFormatter={formatSpeed} width={80} />
          <Tooltip
            contentStyle={{ backgroundColor: '#1a1d27', border: '1px solid #2f3340', borderRadius: 8, fontSize: 12 }}
            labelStyle={{ color: '#9ca3af' }}
            formatter={(value: number) => formatSpeed(value)}
          />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          {interfaces.map((name, i) => (
            <Line key={`${name}_rx`} type="monotone" dataKey={`${name}_rx`} name={`${name} RX`} stroke={COLORS[i % COLORS.length]} dot={false} strokeWidth={1.5} />
          ))}
          {interfaces.map((name, i) => (
            <Line key={`${name}_tx`} type="monotone" dataKey={`${name}_tx`} name={`${name} TX`} stroke={COLORS[i % COLORS.length]} strokeDasharray="4 2" dot={false} strokeWidth={1.5} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
```

- [ ] **Step 3: Write InterfaceList component**

```tsx
// frontend/src/components/InterfaceList.tsx
import type { InterfaceTraffic } from '../types'

function formatSpeed(bytesPerSec: number): string {
  if (bytesPerSec < 1024) return `${bytesPerSec.toFixed(0)} B/s`
  if (bytesPerSec < 1024 * 1024) return `${(bytesPerSec / 1024).toFixed(1)} KB/s`
  if (bytesPerSec < 1024 * 1024 * 1024) return `${(bytesPerSec / (1024 * 1024)).toFixed(1)} MB/s`
  return `${(bytesPerSec / (1024 * 1024 * 1024)).toFixed(2)} GB/s`
}

export default function InterfaceList({ interfaces }: { interfaces: InterfaceTraffic[] }) {
  if (!interfaces.length) return null

  return (
    <div className="bg-dark-800 border border-dark-600 rounded-xl p-4">
      <h2 className="text-sm font-semibold text-gray-300 mb-3">Network Interfaces</h2>
      <table className="w-full text-xs">
        <thead>
          <tr className="text-gray-500 border-b border-dark-600">
            <th className="text-left py-2 font-medium">Interface</th>
            <th className="text-left py-2 font-medium">Status</th>
            <th className="text-right py-2 font-medium">RX Speed</th>
            <th className="text-right py-2 font-medium">TX Speed</th>
          </tr>
        </thead>
        <tbody>
          {interfaces.map(iface => (
            <tr key={iface.name} className="border-b border-dark-700">
              <td className="py-2 text-gray-300 font-mono">{iface.name}</td>
              <td className="py-2">
                <span className={`inline-block w-2 h-2 rounded-full mr-1.5 ${iface.is_up ? 'bg-emerald-500' : 'bg-red-500'}`} />
                <span className="text-gray-400">{iface.is_up ? 'UP' : 'DOWN'}</span>
              </td>
              <td className="py-2 text-right text-gray-300 font-mono">{formatSpeed(iface.rx_speed)}</td>
              <td className="py-2 text-right text-gray-300 font-mono">{formatSpeed(iface.tx_speed)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

- [ ] **Step 4: Write DashboardPage**

```tsx
// frontend/src/pages/DashboardPage.tsx
import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'
import { useWebSocket } from '../hooks/useWebSocket'
import ServerLoad from '../components/ServerLoad'
import TrafficChart from '../components/TrafficChart'
import InterfaceList from '../components/InterfaceList'
import type { SystemMetrics, TrafficSnapshot } from '../types'

const MAX_HISTORY = 300

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null)
  const [trafficHistory, setTrafficHistory] = useState<TrafficSnapshot[]>([])
  const { data: trafficData } = useWebSocket<TrafficSnapshot>('/api/ws/traffic')

  const fetchMetrics = useCallback(async () => {
    try {
      const m = await api.get<SystemMetrics>('/api/metrics/system')
      setMetrics(m)
    } catch {}
  }, [])

  useEffect(() => {
    fetchMetrics()
    const interval = setInterval(fetchMetrics, 3000)
    return () => clearInterval(interval)
  }, [fetchMetrics])

  useEffect(() => {
    if (trafficData) {
      setTrafficHistory(prev => {
        const next = [...prev, trafficData]
        return next.length > MAX_HISTORY ? next.slice(-MAX_HISTORY) : next
      })
    }
  }, [trafficData])

  const latestInterfaces = trafficData?.interfaces || []

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold text-gray-200">Dashboard</h1>
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <div className="lg:col-span-1">
          <ServerLoad metrics={metrics} />
        </div>
        <div className="lg:col-span-3">
          <TrafficChart history={trafficHistory} />
        </div>
      </div>
      <InterfaceList interfaces={latestInterfaces} />
    </div>
  )
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ServerLoad.tsx frontend/src/components/TrafficChart.tsx frontend/src/components/InterfaceList.tsx frontend/src/pages/DashboardPage.tsx
git commit -m "feat: dashboard page with server load, traffic chart, interfaces"
```

---

## Task 15: Frontend — Load Balancer Page

**Files:**
- Create: `frontend/src/components/ProviderTable.tsx`
- Create: `frontend/src/components/ProviderForm.tsx`
- Create: `frontend/src/pages/LoadBalancerPage.tsx`

- [ ] **Step 1: Write ProviderTable component**

```tsx
// frontend/src/components/ProviderTable.tsx
import type { LBProvider } from '../types'

interface Props {
  providers: LBProvider[]
  mode: string
  onDelete: (id: number) => void
  onEdit: (p: LBProvider) => void
}

export default function ProviderTable({ providers, mode, onDelete, onEdit }: Props) {
  return (
    <div className="bg-dark-800 border border-dark-600 rounded-xl p-4">
      <h2 className="text-sm font-semibold text-gray-300 mb-3">Providers</h2>
      <table className="w-full text-xs">
        <thead>
          <tr className="text-gray-500 border-b border-dark-600">
            <th className="text-left py-2 font-medium">Name</th>
            <th className="text-left py-2 font-medium">Gateway</th>
            <th className="text-left py-2 font-medium">Interface</th>
            <th className="text-center py-2 font-medium">{mode === 'round-robin' ? 'Weight' : 'Priority'}</th>
            <th className="text-center py-2 font-medium">Health</th>
            <th className="text-center py-2 font-medium">Active</th>
            <th className="text-right py-2 font-medium">Actions</th>
          </tr>
        </thead>
        <tbody>
          {providers.map(p => (
            <tr key={p.id} className="border-b border-dark-700">
              <td className="py-2 text-gray-300">{p.name}</td>
              <td className="py-2 text-gray-400 font-mono">{p.gateway_ip}</td>
              <td className="py-2 text-gray-400 font-mono">{p.interface}</td>
              <td className="py-2 text-center text-gray-300">
                {mode === 'round-robin' ? p.weight : p.priority === 1 ? 'Primary' : 'Backup'}
              </td>
              <td className="py-2 text-center">
                <span className={`inline-block w-2.5 h-2.5 rounded-full ${p.is_healthy ? 'bg-emerald-500' : 'bg-red-500'}`} />
              </td>
              <td className="py-2 text-center">
                <span className={`text-xs ${p.is_active ? 'text-emerald-400' : 'text-gray-500'}`}>
                  {p.is_active ? 'Yes' : 'No'}
                </span>
              </td>
              <td className="py-2 text-right space-x-2">
                <button onClick={() => onEdit(p)} className="text-gray-400 hover:text-accent transition">Edit</button>
                <button onClick={() => onDelete(p.id)} className="text-gray-400 hover:text-red-400 transition">Del</button>
              </td>
            </tr>
          ))}
          {!providers.length && (
            <tr><td colSpan={7} className="py-4 text-center text-gray-500">No providers configured</td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
```

- [ ] **Step 2: Write ProviderForm component**

```tsx
// frontend/src/components/ProviderForm.tsx
import { useState, useEffect, FormEvent } from 'react'
import type { LBProvider } from '../types'

interface Props {
  mode: string
  editing: LBProvider | null
  onSave: (data: { name: string; gateway_ip: string; interface: string; weight: number; priority: number }) => void
  onCancel: () => void
}

export default function ProviderForm({ mode, editing, onSave, onCancel }: Props) {
  const [name, setName] = useState('')
  const [gatewayIp, setGatewayIp] = useState('')
  const [iface, setIface] = useState('')
  const [weight, setWeight] = useState(50)
  const [priority, setPriority] = useState(1)

  useEffect(() => {
    if (editing) {
      setName(editing.name)
      setGatewayIp(editing.gateway_ip)
      setIface(editing.interface)
      setWeight(editing.weight)
      setPriority(editing.priority)
    }
  }, [editing])

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    onSave({ name, gateway_ip: gatewayIp, interface: iface, weight, priority })
  }

  const inputClass = 'w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-accent transition'

  return (
    <div className="bg-dark-800 border border-dark-600 rounded-xl p-4">
      <h2 className="text-sm font-semibold text-gray-300 mb-3">
        {editing ? 'Edit Provider' : 'Add Provider'}
      </h2>
      <form onSubmit={handleSubmit} className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Name</label>
          <input value={name} onChange={e => setName(e.target.value)} className={inputClass} required placeholder="ISP1" />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">Gateway IP</label>
          <input value={gatewayIp} onChange={e => setGatewayIp(e.target.value)} className={inputClass} required placeholder="192.168.1.1" />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">Interface</label>
          <input value={iface} onChange={e => setIface(e.target.value)} className={inputClass} required placeholder="eth0" />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">
            {mode === 'round-robin' ? 'Weight (1-100)' : 'Priority (1=Primary, 2=Backup)'}
          </label>
          {mode === 'round-robin' ? (
            <input type="number" min={1} max={100} value={weight} onChange={e => setWeight(+e.target.value)} className={inputClass} />
          ) : (
            <select value={priority} onChange={e => setPriority(+e.target.value)} className={inputClass}>
              <option value={1}>Primary</option>
              <option value={2}>Backup</option>
            </select>
          )}
        </div>
        <div className="col-span-2 flex gap-2 justify-end">
          <button type="button" onClick={onCancel} className="px-4 py-2 text-xs text-gray-400 hover:text-gray-200 transition">Cancel</button>
          <button type="submit" className="px-4 py-2 bg-accent hover:bg-accent-light text-dark-900 rounded-lg text-xs font-semibold transition">
            {editing ? 'Update' : 'Add'}
          </button>
        </div>
      </form>
    </div>
  )
}
```

- [ ] **Step 3: Write LoadBalancerPage**

```tsx
// frontend/src/pages/LoadBalancerPage.tsx
import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'
import ProviderTable from '../components/ProviderTable'
import ProviderForm from '../components/ProviderForm'
import type { LBConfig, LBProvider } from '../types'

export default function LoadBalancerPage() {
  const [config, setConfig] = useState<LBConfig | null>(null)
  const [providers, setProviders] = useState<LBProvider[]>([])
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<LBProvider | null>(null)
  const [error, setError] = useState('')

  const fetchData = useCallback(async () => {
    try {
      const status = await api.get<{ config: LBConfig; providers: LBProvider[] }>('/api/lb/status')
      setConfig(status.config)
      setProviders(status.providers)
    } catch {}
  }, [])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [fetchData])

  const handleModeChange = async (mode: string) => {
    try {
      const updated = await api.put<LBConfig>('/api/lb/config', { ...config, mode })
      setConfig(updated)
    } catch (e: any) { setError(e.message) }
  }

  const handleToggleEnabled = async () => {
    if (!config) return
    try {
      const updated = await api.put<LBConfig>('/api/lb/config', { ...config, is_enabled: !config.is_enabled })
      setConfig(updated)
    } catch (e: any) { setError(e.message) }
  }

  const handleSave = async (data: { name: string; gateway_ip: string; interface: string; weight: number; priority: number }) => {
    try {
      if (editing) {
        await api.put(`/api/lb/providers/${editing.id}`, data)
      } else {
        await api.post('/api/lb/providers', data)
      }
      setShowForm(false)
      setEditing(null)
      fetchData()
    } catch (e: any) { setError(e.message) }
  }

  const handleDelete = async (id: number) => {
    try {
      await api.del(`/api/lb/providers/${id}`)
      fetchData()
    } catch (e: any) { setError(e.message) }
  }

  const handleEdit = (p: LBProvider) => {
    setEditing(p)
    setShowForm(true)
  }

  if (!config) return <div className="text-gray-500">Loading...</div>

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-gray-200">Load Balancer</h1>
        <div className="flex items-center gap-3">
          <button
            onClick={handleToggleEnabled}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              config.is_enabled
                ? 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30'
                : 'bg-dark-700 text-gray-400 hover:bg-dark-600'
            }`}
          >
            {config.is_enabled ? 'Enabled' : 'Disabled'}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-400/10 text-red-400 text-sm px-3 py-2 rounded-lg">
          {error}
          <button onClick={() => setError('')} className="ml-2 text-red-300 hover:text-red-200">✕</button>
        </div>
      )}

      {/* Mode selector */}
      <div className="bg-dark-800 border border-dark-600 rounded-xl p-4">
        <h2 className="text-sm font-semibold text-gray-300 mb-3">Mode</h2>
        <div className="flex gap-2">
          {['round-robin', 'failover'].map(mode => (
            <button
              key={mode}
              onClick={() => handleModeChange(mode)}
              className={`px-4 py-2 rounded-lg text-xs font-medium transition ${
                config.mode === mode
                  ? 'bg-accent/20 text-accent border border-accent/30'
                  : 'bg-dark-700 text-gray-400 hover:bg-dark-600 border border-transparent'
              }`}
            >
              {mode === 'round-robin' ? 'Round Robin' : 'Failover'}
            </button>
          ))}
        </div>
        <p className="text-xs text-gray-500 mt-2">
          {config.mode === 'round-robin'
            ? 'Traffic distributed across providers by weight'
            : 'Primary provider with automatic failover to backup'}
        </p>
      </div>

      <ProviderTable providers={providers} mode={config.mode} onDelete={handleDelete} onEdit={handleEdit} />

      {showForm || editing ? (
        <ProviderForm
          mode={config.mode}
          editing={editing}
          onSave={handleSave}
          onCancel={() => { setShowForm(false); setEditing(null) }}
        />
      ) : (
        <button
          onClick={() => setShowForm(true)}
          className="w-full py-2.5 border border-dashed border-dark-600 rounded-xl text-xs text-gray-500 hover:text-accent hover:border-accent/30 transition"
        >
          + Add Provider
        </button>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ProviderTable.tsx frontend/src/components/ProviderForm.tsx frontend/src/pages/LoadBalancerPage.tsx
git commit -m "feat: load balancer page with provider management"
```

---

## Task 16: System Integration — Systemd + Install Script

**Files:**
- Modify: `config/systemd/blackwall.service` (currently empty or stub)
- Modify: `scripts/install.sh`

- [ ] **Step 1: Write systemd service**

```ini
# config/systemd/blackwall.service
[Unit]
Description=The Blackwall Firewall Manager
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/blackwall
Environment=BLACKWALL_SECRET_KEY=CHANGE_ME_ON_INSTALL
ExecStart=/opt/blackwall/venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8443
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 2: Write install script**

```bash
#!/bin/bash
# scripts/install.sh — The Blackwall installer for Ubuntu 22.04
set -euo pipefail

INSTALL_DIR="/opt/blackwall"
SERVICE_NAME="blackwall"

echo "=== The Blackwall Installer ==="

# Check Ubuntu
if ! grep -q "Ubuntu 22" /etc/os-release 2>/dev/null; then
    echo "Warning: This installer is designed for Ubuntu 22.04"
fi

# Check root
if [[ $EUID -ne 0 ]]; then
    echo "Error: Run as root (sudo)"
    exit 1
fi

# Install system dependencies
echo "[1/6] Installing system dependencies..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv nodejs npm curl iputils-ping iproute2

# Create install directory
echo "[2/6] Setting up $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
cp -r . "$INSTALL_DIR/"

# Python venv + deps
echo "[3/6] Setting up Python environment..."
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install -q -r "$INSTALL_DIR/backend/requirements.txt"

# Frontend build
echo "[4/6] Building frontend..."
cd "$INSTALL_DIR/frontend"
npm install --silent
npm run build
cd "$INSTALL_DIR"

# Generate secret key
SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Install systemd service
echo "[5/6] Installing systemd service..."
sed "s/CHANGE_ME_ON_INSTALL/$SECRET/" "$INSTALL_DIR/config/systemd/blackwall.service" > /etc/systemd/system/${SERVICE_NAME}.service
systemctl daemon-reload
systemctl enable ${SERVICE_NAME}
systemctl start ${SERVICE_NAME}

echo "[6/6] Done!"
echo ""
echo "=== The Blackwall is running ==="
echo "Access: http://$(hostname -I | awk '{print $1}'):8443"
echo "First login will prompt you to create the root account."
```

- [ ] **Step 3: Make install script executable**

Run: `chmod +x /Users/denisgumen/Desktop/code/The-Blackwall/scripts/install.sh`

- [ ] **Step 4: Commit**

```bash
git add config/systemd/blackwall.service scripts/install.sh
git commit -m "feat: systemd service + install script for Ubuntu 22.04"
```

---

## Task 17: Serve Frontend Static Files from Backend

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Add static file serving to main.py**

After all routers, add frontend static serving for production:

```python
# Add to the end of backend/app/main.py
import os
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Serve built frontend in production
frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="static")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("ws/"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404)
        file_path = frontend_dist / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")
```

- [ ] **Step 2: Run all backend tests to verify nothing broke**

Run: `cd /Users/denisgumen/Desktop/code/The-Blackwall/backend && python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: serve frontend static files from FastAPI in production"
```

---

## Task 18: Final Integration Test + Build Verification

- [ ] **Step 1: Run all backend tests**

Run: `cd /Users/denisgumen/Desktop/code/The-Blackwall/backend && python -m pytest tests/ -v --tb=short`
Expected: ALL PASS

- [ ] **Step 2: Check frontend builds**

Run: `cd /Users/denisgumen/Desktop/code/The-Blackwall/frontend && npm run build`
Expected: Build completes with no errors

- [ ] **Step 3: Verify backend starts**

Run: `cd /Users/denisgumen/Desktop/code/The-Blackwall && python -m uvicorn backend.app.main:app --port 8000 &`
Wait 2s, then:
Run: `curl -s http://localhost:8000/api/auth/me | head -c 200`
Expected: 401 response (not authenticated — confirms server is running)
Then kill the server.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore: final integration verification"
```

---

## Task 19: Update Project Documentation

**Files:**
- Modify: `README.md`
- Modify: `plan/plan.md` (add note about load balancer feature)
- Modify: `docs/DEVELOPMENT.md`

- [ ] **Step 1: Update README.md with current state**

Add sections for: Quick Start, Features (Auth, Dashboard, Load Balancer), Development setup.

- [ ] **Step 2: Update DEVELOPMENT.md**

Document: backend setup (venv + pip), frontend setup (npm install + npm run dev), running tests, dev workflow (vite proxy to backend).

- [ ] **Step 3: Commit**

```bash
git add README.md plan/plan.md docs/DEVELOPMENT.md
git commit -m "docs: update README, DEVELOPMENT with MVP setup instructions"
```
