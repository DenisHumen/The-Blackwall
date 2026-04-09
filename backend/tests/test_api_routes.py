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
