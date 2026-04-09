# API Documentation — The Blackwall

Base URL: `http://localhost:8000`  
Swagger UI: `http://localhost:8000/docs`

## Аутентификация

Все API (кроме setup-check, setup, login) требуют JWT-токен в httpOnly cookie `access_token`.

### GET /api/auth/setup-check
Проверяет, нужна ли первичная настройка.
```json
// Response
{ "needs_setup": true }
```

### POST /api/auth/setup
Создаёт первого root-пользователя. Работает только 1 раз.
```json
// Request
{ "username": "admin", "password": "StrongPass123!" }
// Response: UserResponse
```

### POST /api/auth/login
Rate-limit: 5 попыток / 60 сек.
```json
// Request
{ "username": "admin", "password": "StrongPass123!" }
// Response
{ "message": "ok", "user": { "id": 1, "username": "admin", "role": "root" } }
```

### POST /api/auth/logout
Удаляет cookie `access_token`.

### GET /api/auth/me
Возвращает текущего пользователя.

---

## Метрики системы

### GET /api/metrics/current
Системные метрики в реальном времени.
```json
{
  "cpu_percent": 12.5,
  "memory_percent": 45.2,
  "memory_used_mb": 7264.0,
  "memory_total_mb": 16384.0,
  "disk_percent": 62.1,
  "disk_used_gb": 120.5,
  "disk_total_gb": 256.0,
  "network_rx_bytes": 1234567890,
  "network_tx_bytes": 987654321,
  "network_rx_rate": 15000.5,
  "network_tx_rate": 8000.2,
  "uptime_seconds": 86400,
  "load_avg_1": 1.5,
  "load_avg_5": 1.2,
  "load_avg_15": 0.9,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### GET /api/metrics/traffic?minutes=60
Возвращает историю трафика за N минут (макс 1440).
```json
[
  { "timestamp": "2024-01-01T12:00:00Z", "rx_rate": 15000.5, "tx_rate": 8000.2 }
]
```

---

## Балансировщик нагрузки

### Режимы
- **round_robin**: Распределение трафика между несколькими шлюзами по весам
- **failover**: Один основной шлюз + резервные (переключение при отказе)

### GET /api/loadbalancer/
Список всех конфигураций балансировщика.

### POST /api/loadbalancer/
Создать новую конфигурацию.
```json
{
  "name": "ISP Balancer",
  "mode": "round_robin",
  "gateways": [
    { "address": "192.168.1.1", "interface_name": "eth0", "weight": 2 },
    { "address": "192.168.2.1", "interface_name": "eth1", "weight": 1 }
  ]
}
```

### PATCH /api/loadbalancer/{id}
Обновить конфигурацию (имя, режим, активность).
```json
{ "name": "New Name", "mode": "failover", "is_active": true }
```

### DELETE /api/loadbalancer/{id}
Удалить конфигурацию (204 No Content).

### POST /api/loadbalancer/{id}/gateways
Добавить шлюз.
```json
{ "address": "10.0.0.3", "interface_name": "eth2", "weight": 1, "priority": 2, "is_primary": false }
```

### DELETE /api/loadbalancer/{id}/gateways/{gw_id}
Удалить шлюз (204 No Content).

### POST /api/loadbalancer/{id}/health-check
Запускает ping-проверку всех шлюзов и обновляет их статус.
```json
[
  {
    "id": 1,
    "address": "192.168.1.1",
    "interface_name": "eth0",
    "is_healthy": true,
    "latency_ms": 1.23,
    "last_check": "2024-01-01T12:00:00Z"
  }
]
```