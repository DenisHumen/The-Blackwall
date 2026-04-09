# The Blackwall MVP — Dashboard + Load Balancer

> **Date:** 2026-04-09
> **Target:** Ubuntu 22.04
> **Stack:** FastAPI + React/TS/Tailwind + SQLite (MVP, migration to PostgreSQL+TimescaleDB later via SQLAlchemy ORM abstraction)

## Overview

First working iteration: auth, dashboard with real-time metrics, and load balancer management. The system installs as a systemd service and starts with the OS.

## Architecture

```
Browser (React + TypeScript + TailwindCSS)
    │
    ├── REST API (JSON)
    ├── WebSocket (real-time traffic)
    │
FastAPI Backend (Python 3.10+)
    ├── Auth (JWT, bcrypt)
    ├── System Metrics (/proc/net/dev, /proc/stat, /proc/meminfo)
    ├── Load Balancer Manager (ip route, ip rule, ping)
    └── SQLite via SQLAlchemy ORM
```

## 1. Authentication

### Flow
- First launch: `/api/auth/setup` creates root account (username + password)
- Login: `/api/auth/login` → JWT token (httpOnly cookie, 24h expiry)
- All other endpoints require valid JWT

### Data Model
```
users:
  id: int (PK)
  username: str (unique)
  password_hash: str (bcrypt)
  role: str (root|admin|operator|viewer) — roles stored but NOT enforced in MVP
  is_active: bool
  created_at: datetime
  last_login: datetime
```

### API
- `POST /api/auth/setup` — create root user (only works once)
- `POST /api/auth/login` — returns JWT in httpOnly cookie
- `POST /api/auth/logout` — clears cookie
- `GET /api/auth/me` — current user info

### Security
- Rate limiting on `/api/auth/login`: max 5 attempts per minute per IP
- `/api/auth/setup` disabled after root user exists

## 2. Dashboard

### Server Load Widget
- CPU usage: parse `/proc/stat` (calculate delta between reads)
- RAM usage: parse `/proc/meminfo` (MemTotal, MemAvailable)
- Disk usage: `shutil.disk_usage("/")`
- Update: polling every 3 seconds via `GET /api/metrics/system`

### Traffic Chart
- Source: `/proc/net/dev` — bytes rx/tx per interface
- Delivery: WebSocket `/api/ws/traffic` pushes deltas every 1 second
- Auto-scaling Y axis: B/s → KB/s → MB/s → GB/s based on current max value
- Chart library: Recharts (React-native, lightweight)
- Time window: last 5 minutes (300 data points)
- Multiple interfaces on same chart, color-coded

### Network Interfaces List
- Name, IP, current speed (rx/tx per second), status (up/down)

## 3. Load Balancer

### Modes
1. **Round-Robin** — distribute traffic across multiple provider gateways
2. **Failover** — primary + backup, instant switch on failure

### Data Model
```
lb_config (singleton — exactly one row):
  id: int (PK)
  mode: str (round-robin|failover)
  check_interval: int (seconds, default 2; auto-set to 1 in failover mode)
  check_timeout: int (ms, default 1000)
  check_target: str (default "8.8.8.8" — external target pinged via each gateway for true connectivity check)
  updated_at: datetime

lb_providers:
  id: int (PK)
  name: str
  gateway_ip: str
  interface: str
  weight: int (1-100, for round-robin)
  priority: int (for failover: 1=primary, 2=backup)
  is_active: bool
  is_healthy: bool
  last_check: datetime
  created_at: datetime
```

### Round-Robin Implementation
```bash
# Multipath routing with nexthop weights
ip route replace default \
  nexthop via <gateway1> dev <iface1> weight <w1> \
  nexthop via <gateway2> dev <iface2> weight <w2>
```
Uses Linux multipath routing with weighted nexthops for per-flow distribution.

### Failover Implementation
```bash
# Default route via primary
ip route replace default via <primary_gateway>
# Background monitor pings primary every 2s
# On 3 consecutive failures → switch:
ip route replace default via <backup_gateway>
# Continue monitoring primary, restore when back
```
Target failover time: < 5 seconds (check_interval=1s in failover mode, 3 consecutive failures × ~1.5s each).

### Health Monitor
- Background asyncio task
- ICMP ping to `check_target` (default 8.8.8.8) via each gateway's routing table every `check_interval` seconds
- Gateway marked unhealthy after 3 consecutive failures
- Gateway marked healthy after 2 consecutive successes
- Events logged and pushed via WebSocket

### Edge Cases
- All providers fail: keep last known route, show critical alert in UI
- Delete last active provider: reject with error, require at least one active provider
- Mode switch while active: gracefully tear down current routing, apply new mode config
- Provider added while running: hot-add to routing without disrupting existing flows

### WebSocket Authentication
WebSocket `/api/ws/traffic` validates JWT from httpOnly cookie during the upgrade handshake. Connection rejected if cookie missing or token expired.

### API
- `GET /api/metrics/system` — CPU, RAM, Disk usage
- `GET /api/lb/config` — current mode and settings
- `PUT /api/lb/config` — update mode/settings
- `GET /api/lb/providers` — list providers with health status
- `POST /api/lb/providers` — add provider
- `PUT /api/lb/providers/{id}` — update provider
- `DELETE /api/lb/providers/{id}` — remove provider
- `GET /api/lb/status` — real-time status of all providers

## 4. Frontend Pages

### Login Page
- Dark theme, centered card
- Logo "The Blackwall" at top
- Username + password fields
- Error messages inline
- First-visit detection → setup form (create root)

### Dashboard Page
- Top: server name + uptime
- Left column: CPU/RAM/Disk gauges (circular progress or bars)
- Center: traffic chart (full width, auto-scaling)
- Bottom: network interfaces table

### Load Balancer Page
- Mode selector (toggle: Round-Robin / Failover)
- Provider table: name, gateway, interface, weight/priority, health status (green/red dot), actions
- Add provider form (slide-out panel)
- Status indicators update in real-time

### Design System
- Dark theme (gray-900 background, gray-800 cards)
- Accent color: cyan-500 (#06b6d4)
- Font: Inter or system sans-serif
- Compact spacing, no wasted space
- Responsive but desktop-first (admin panel)

## 5. System Integration

### Systemd Service
```ini
[Unit]
Description=The Blackwall Firewall Manager
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/blackwall
ExecStart=/opt/blackwall/venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8443
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

### Install Script
- Check Ubuntu 22.04
- Install Python 3.10+, pip, venv
- Create /opt/blackwall, copy files
- Create venv, install dependencies
- Initialize SQLite database
- Enable and start systemd service
- Print access URL

## 6. File Structure (new/modified files)

```
backend/
  app/
    main.py              — FastAPI app, CORS, routes, WebSocket
    config.py            — Settings (SECRET_KEY, DB path, etc.)
    database.py          — SQLAlchemy engine + session
    models/
      user.py            — User model
      loadbalancer.py    — LB config + provider models
    schemas/
      auth.py            — Login/setup request/response
      metrics.py         — System metrics response
      loadbalancer.py    — LB config/provider schemas
    api/
      auth.py            — Auth endpoints
      metrics.py         — System metrics + WebSocket
      loadbalancer.py    — LB CRUD + status
    core/
      auth.py            — JWT create/verify, password hashing
      metrics.py         — /proc parsers for CPU/RAM/traffic
      lb_engine.py       — ip route/rule management
      lb_monitor.py      — Background health checker
  requirements.txt       — Updated dependencies

frontend/
  package.json           — Dependencies (react, recharts, tailwind, etc.)
  vite.config.ts         — Vite config with API proxy
  tailwind.config.js     — Dark theme config
  src/
    main.tsx             — Entry point
    App.tsx              — Router setup
    api/client.ts        — Axios instance with auth
    pages/
      LoginPage.tsx      — Auth page
      DashboardPage.tsx  — Metrics dashboard
      LoadBalancerPage.tsx — LB management
    components/
      ServerLoad.tsx     — CPU/RAM/Disk gauges
      TrafficChart.tsx   — Real-time traffic chart
      InterfaceList.tsx  — Network interfaces
      ProviderTable.tsx  — LB providers table
      ProviderForm.tsx   — Add/edit provider
    hooks/
      useAuth.ts         — Auth state management
      useWebSocket.ts    — WebSocket connection hook
    types/
      index.ts           — All TypeScript types

scripts/
  install.sh             — Installation script for Ubuntu 22.04

config/
  systemd/blackwall.service — Systemd unit file
```

## 7. Testing Strategy

- Backend: pytest with TestClient (FastAPI), SQLite in-memory for tests
- Auth: test login/logout/setup flows, JWT validation, invalid credentials
- Metrics: mock /proc files, test parsing correctness
- LB: mock subprocess calls (ip route/rule), test failover logic
- Frontend: basic smoke tests with Vitest
