import pytest
from httpx import AsyncClient


@pytest.fixture
async def auth_client(client: AsyncClient):
    """Client that is already authenticated as root."""
    # Clear rate limiter state for tests
    from app.api.auth import _login_attempts
    _login_attempts.clear()

    await client.post("/api/auth/setup", json={"username": "root", "password": "TestPass123!"})
    resp = await client.post("/api/auth/login", json={"username": "root", "password": "TestPass123!"})
    assert resp.status_code == 200
    return client


# ---- Metrics ----

@pytest.mark.asyncio
async def test_metrics_current_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/metrics/current")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_metrics_current(auth_client: AsyncClient):
    resp = await auth_client.get("/api/metrics/current")
    assert resp.status_code == 200
    data = resp.json()
    assert "cpu_percent" in data
    assert "memory_percent" in data
    assert "disk_percent" in data
    assert "network_rx_rate" in data
    assert "uptime_seconds" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_metrics_traffic(auth_client: AsyncClient):
    resp = await auth_client.get("/api/metrics/traffic?minutes=5")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


# ---- Setup Check ----

@pytest.mark.asyncio
async def test_setup_check_needs_setup(client: AsyncClient):
    resp = await client.get("/api/auth/setup-check")
    assert resp.status_code == 200
    assert resp.json()["needs_setup"] is True


@pytest.mark.asyncio
async def test_setup_check_after_setup(client: AsyncClient):
    await client.post("/api/auth/setup", json={"username": "root", "password": "TestPass123!"})
    resp = await client.get("/api/auth/setup-check")
    assert resp.status_code == 200
    assert resp.json()["needs_setup"] is False


# ---- Load Balancer CRUD ----

@pytest.mark.asyncio
async def test_lb_list_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/loadbalancer")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_lb_create_and_list(auth_client: AsyncClient):
    payload = {
        "name": "Test LB",
        "mode": "round_robin",
        "gateways": [
            {"address": "192.168.1.1", "interface_name": "eth0", "weight": 2},
            {"address": "192.168.1.2", "interface_name": "eth1", "weight": 1},
        ],
    }
    resp = await auth_client.post("/api/loadbalancer", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test LB"
    assert data["mode"] == "round_robin"
    assert len(data["gateways"]) == 2
    lb_id = data["id"]

    # List
    resp = await auth_client.get("/api/loadbalancer")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["id"] == lb_id


@pytest.mark.asyncio
async def test_lb_update(auth_client: AsyncClient):
    resp = await auth_client.post("/api/loadbalancer", json={
        "name": "Orig",
        "mode": "round_robin",
        "gateways": [{"address": "10.0.0.1", "interface_name": "eth0"}],
    })
    lb_id = resp.json()["id"]

    resp = await auth_client.patch(f"/api/loadbalancer/{lb_id}", json={"name": "Updated", "is_active": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_lb_delete(auth_client: AsyncClient):
    resp = await auth_client.post("/api/loadbalancer", json={
        "name": "ToDelete",
        "mode": "failover",
        "gateways": [{"address": "10.0.0.1", "interface_name": "eth0", "is_primary": True}],
    })
    lb_id = resp.json()["id"]

    resp = await auth_client.delete(f"/api/loadbalancer/{lb_id}")
    assert resp.status_code == 204

    resp = await auth_client.get(f"/api/loadbalancer/{lb_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_lb_add_gateway(auth_client: AsyncClient):
    resp = await auth_client.post("/api/loadbalancer", json={
        "name": "GW Test",
        "mode": "round_robin",
        "gateways": [{"address": "10.0.0.1", "interface_name": "eth0"}],
    })
    lb_id = resp.json()["id"]

    resp = await auth_client.post(f"/api/loadbalancer/{lb_id}/gateways", json={
        "address": "10.0.0.2",
        "interface_name": "eth1",
        "weight": 3,
    })
    assert resp.status_code == 201
    gw = resp.json()
    assert gw["address"] == "10.0.0.2"
    assert gw["weight"] == 3

    # Verify gateway was added
    resp = await auth_client.get(f"/api/loadbalancer/{lb_id}")
    assert len(resp.json()["gateways"]) == 2


@pytest.mark.asyncio
async def test_lb_remove_gateway(auth_client: AsyncClient):
    resp = await auth_client.post("/api/loadbalancer", json={
        "name": "GW Del",
        "mode": "round_robin",
        "gateways": [
            {"address": "10.0.0.1", "interface_name": "eth0"},
            {"address": "10.0.0.2", "interface_name": "eth1"},
        ],
    })
    lb_id = resp.json()["id"]
    gw_id = resp.json()["gateways"][1]["id"]

    resp = await auth_client.delete(f"/api/loadbalancer/{lb_id}/gateways/{gw_id}")
    assert resp.status_code == 204

    resp = await auth_client.get(f"/api/loadbalancer/{lb_id}")
    assert len(resp.json()["gateways"]) == 1


@pytest.mark.asyncio
async def test_lb_invalid_mode(auth_client: AsyncClient):
    resp = await auth_client.post("/api/loadbalancer", json={
        "name": "Bad Mode",
        "mode": "invalid_mode",
        "gateways": [{"address": "10.0.0.1", "interface_name": "eth0"}],
    })
    assert resp.status_code == 400


# ---- Firewall Rules ----

@pytest.mark.asyncio
async def test_rules_stats_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/rules/stats")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_rules_stats(auth_client: AsyncClient):
    resp = await auth_client.get("/api/rules/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "totalRules" in data
    assert "activeRules" in data
    assert "blockedToday" in data
    assert "threatsDetected" in data
    assert data["totalRules"] == 0


@pytest.mark.asyncio
async def test_rules_create_and_list(auth_client: AsyncClient):
    payload = {
        "name": "Block SSH brute force",
        "source_ip": "0.0.0.0/0",
        "dest_port": "22",
        "protocol": "tcp",
        "direction": "in",
        "action": "drop",
        "priority": 10,
    }
    resp = await auth_client.post("/api/rules", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Block SSH brute force"
    assert data["action"] == "drop"
    assert data["is_system"] is False
    rule_id = data["id"]

    # List
    resp = await auth_client.get("/api/rules")
    assert resp.status_code == 200
    rules = resp.json()
    assert len(rules) == 1
    assert rules[0]["id"] == rule_id

    # Stats should reflect the new rule
    resp = await auth_client.get("/api/rules/stats")
    assert resp.json()["totalRules"] == 1
    assert resp.json()["activeRules"] == 1


@pytest.mark.asyncio
async def test_rules_get_single(auth_client: AsyncClient):
    resp = await auth_client.post("/api/rules", json={
        "name": "Allow HTTPS",
        "dest_port": "443",
        "protocol": "tcp",
        "action": "accept",
    })
    rule_id = resp.json()["id"]

    resp = await auth_client.get(f"/api/rules/{rule_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Allow HTTPS"


@pytest.mark.asyncio
async def test_rules_get_not_found(auth_client: AsyncClient):
    resp = await auth_client.get("/api/rules/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_rules_update(auth_client: AsyncClient):
    resp = await auth_client.post("/api/rules", json={
        "name": "Temp Rule",
        "action": "drop",
    })
    rule_id = resp.json()["id"]

    resp = await auth_client.patch(f"/api/rules/{rule_id}", json={
        "name": "Updated Rule",
        "is_active": False,
    })
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Rule"
    assert resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_rules_delete(auth_client: AsyncClient):
    resp = await auth_client.post("/api/rules", json={
        "name": "To Delete",
        "action": "drop",
    })
    rule_id = resp.json()["id"]

    resp = await auth_client.delete(f"/api/rules/{rule_id}")
    assert resp.status_code == 204

    resp = await auth_client.get(f"/api/rules/{rule_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_rules_invalid_action(auth_client: AsyncClient):
    resp = await auth_client.post("/api/rules", json={
        "name": "Bad action",
        "action": "nuke",
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_rules_invalid_direction(auth_client: AsyncClient):
    resp = await auth_client.post("/api/rules", json={
        "name": "Bad dir",
        "direction": "sideways",
        "action": "drop",
    })
    assert resp.status_code == 400


# ---- Firewall Logs ----

@pytest.mark.asyncio
async def test_logs_recent_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/logs/recent")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logs_recent_empty(auth_client: AsyncClient):
    resp = await auth_client.get("/api/logs/recent?limit=8")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.asyncio
async def test_logs_list_empty(auth_client: AsyncClient):
    resp = await auth_client.get("/api/logs")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_logs_recent_with_data(auth_client: AsyncClient, db_session):
    """Insert log entries directly and verify /recent returns them."""
    from app.models.log import FirewallLog
    from datetime import datetime, timezone

    log1 = FirewallLog(
        action="block", severity="warning",
        source_ip="192.168.1.100", dest_ip="10.0.0.1",
        dest_port=22, protocol="tcp",
        message="SSH brute force attempt",
        timestamp=datetime.now(timezone.utc),
    )
    log2 = FirewallLog(
        action="allow", severity="info",
        source_ip="10.0.0.5", dest_ip="10.0.0.1",
        dest_port=443, protocol="tcp",
        message="HTTPS traffic",
        timestamp=datetime.now(timezone.utc),
    )
    db_session.add_all([log1, log2])
    await db_session.commit()

    resp = await auth_client.get("/api/logs/recent?limit=8")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    # Check structure
    for item in data:
        assert "id" in item
        assert "time" in item
        assert "action" in item
        assert "source" in item
        assert "message" in item


@pytest.mark.asyncio
async def test_logs_filter_by_action(auth_client: AsyncClient, db_session):
    from app.models.log import FirewallLog
    from datetime import datetime, timezone

    db_session.add_all([
        FirewallLog(action="block", severity="warning", source_ip="1.2.3.4",
                    message="blocked", timestamp=datetime.now(timezone.utc)),
        FirewallLog(action="allow", severity="info", source_ip="5.6.7.8",
                    message="allowed", timestamp=datetime.now(timezone.utc)),
    ])
    await db_session.commit()

    resp = await auth_client.get("/api/logs?action=block")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["action"] == "block"


@pytest.mark.asyncio
async def test_logs_filter_by_source_ip(auth_client: AsyncClient, db_session):
    from app.models.log import FirewallLog
    from datetime import datetime, timezone

    db_session.add_all([
        FirewallLog(action="block", severity="info", source_ip="10.10.10.10",
                    message="test1", timestamp=datetime.now(timezone.utc)),
        FirewallLog(action="block", severity="info", source_ip="20.20.20.20",
                    message="test2", timestamp=datetime.now(timezone.utc)),
    ])
    await db_session.commit()

    resp = await auth_client.get("/api/logs?source_ip=10.10.10.10")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["source_ip"] == "10.10.10.10"
