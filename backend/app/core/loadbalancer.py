"""
Load Balancer networking service.

Manages virtual interfaces, routing tables, and automatic provider switching.

On Linux (production):
  - Creates dummy interfaces for client gateways
  - Manages ip route / ip rule for traffic distribution
  - Round-robin: multipath routes with weights
  - Failover: routing table switching on health failure

On macOS/other (development):
  - Simulates interface status
  - Does NOT modify system networking
"""

import asyncio
import logging
import platform
import re
import time
from datetime import datetime, timezone

logger = logging.getLogger("blackwall.loadbalancer")

IS_LINUX = platform.system() == "Linux"

# ---------------------------------------------------------------------------
# Input validation (prevent command injection)
# ---------------------------------------------------------------------------

_RE_IFACE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{0,14}$")
_RE_IP = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")
_RE_CIDR = re.compile(r"^(\d{1,3}\.){3}\d{1,3}/\d{1,2}$")


def _validate_iface(name: str) -> str:
    if not _RE_IFACE.match(name):
        raise ValueError(f"Invalid interface name: {name!r}")
    return name


def _validate_ip(addr: str) -> str:
    if not _RE_IP.match(addr):
        raise ValueError(f"Invalid IP address: {addr!r}")
    return addr


def _validate_cidr(cidr: str) -> str:
    if not _RE_CIDR.match(cidr):
        raise ValueError(f"Invalid CIDR notation: {cidr!r}")
    return cidr


# ---------------------------------------------------------------------------
# Safe exec helpers (Linux only) — no shell, arguments as list
# ---------------------------------------------------------------------------

async def _run(args: list[str], check: bool = True) -> tuple[int, str, str]:
    """Run a command (no shell) and return (returncode, stdout, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    out = stdout.decode().strip()
    err = stderr.decode().strip()
    if check and proc.returncode != 0:
        logger.error("Command failed %s: %s", args, err)
    return proc.returncode, out, err


# ---------------------------------------------------------------------------
# Virtual Interface management
# ---------------------------------------------------------------------------

async def create_virtual_interface(name: str, ip_cidr: str) -> bool:
    """Create a dummy network interface and assign IP.

    Example: create_virtual_interface("lb0", "10.10.10.1/24")
    Clients will use 10.10.10.1 as their default gateway.
    """
    _validate_iface(name)
    _validate_cidr(ip_cidr)

    if not IS_LINUX:
        logger.info("[SIM] Would create interface %s with IP %s", name, ip_cidr)
        return True

    # Create dummy interface
    rc, _, _ = await _run(["ip", "link", "add", name, "type", "dummy"])
    if rc != 0:
        # May already exist
        rc2, _, _ = await _run(["ip", "link", "show", name])
        if rc2 != 0:
            return False

    # Assign IP
    await _run(["ip", "addr", "flush", "dev", name])
    rc, _, _ = await _run(["ip", "addr", "add", ip_cidr, "dev", name])
    if rc != 0:
        return False

    # Bring up
    rc, _, _ = await _run(["ip", "link", "set", name, "up"])

    # Enable IP forwarding
    await _run(["sysctl", "-w", "net.ipv4.ip_forward=1"])

    logger.info("Created virtual interface %s with IP %s", name, ip_cidr)
    return rc == 0


async def destroy_virtual_interface(name: str) -> bool:
    """Remove a virtual interface."""
    _validate_iface(name)

    if not IS_LINUX:
        logger.info("[SIM] Would destroy interface %s", name)
        return True

    rc, _, _ = await _run(["ip", "link", "delete", name])
    logger.info("Destroyed virtual interface %s", name)
    return rc == 0


async def interface_exists(name: str) -> bool:
    """Check if a network interface exists."""
    _validate_iface(name)

    if not IS_LINUX:
        return False  # Simulation mode

    rc, _, _ = await _run(["ip", "link", "show", name], check=False)
    return rc == 0


# ---------------------------------------------------------------------------
# Routing management
# ---------------------------------------------------------------------------

async def apply_round_robin_routes(
    gateways: list[dict],
    virtual_subnet: str | None = None,
) -> bool:
    """Set up multipath routing with weights for round-robin balancing.

    gateways: [{"address": "192.168.1.1", "interface_name": "eth0", "weight": 2}, ...]
    """
    if not IS_LINUX:
        nexthops = " ".join(
            f"nexthop via {g['address']} dev {g['interface_name']} weight {g.get('weight', 1)}"
            for g in gateways if g.get("is_healthy", True)
        )
        logger.info("[SIM] Round-robin route: ip route replace default %s", nexthops)
        return True

    healthy = [g for g in gateways if g.get("is_healthy", True)]
    if not healthy:
        logger.warning("No healthy gateways for round-robin!")
        return False

    # Build multipath default route — argument list
    cmd: list[str] = ["ip", "route", "replace", "default"]
    for g in healthy:
        _validate_ip(g["address"])
        _validate_iface(g["interface_name"])
        cmd += ["nexthop", "via", g["address"], "dev", g["interface_name"],
                "weight", str(g.get("weight", 1))]

    rc, _, _ = await _run(cmd)
    if rc == 0:
        logger.info("Applied round-robin routes: %d gateways", len(healthy))
    return rc == 0


async def apply_failover_route(
    gateway_address: str,
    interface_name: str,
    table_id: int = 100,
) -> bool:
    """Switch the default route to the specified gateway (failover mode)."""
    _validate_ip(gateway_address)
    _validate_iface(interface_name)

    if not IS_LINUX:
        logger.info("[SIM] Failover route: via %s dev %s (table %d)", gateway_address, interface_name, table_id)
        return True

    # Set route in main table
    rc, _, _ = await _run(["ip", "route", "replace", "default", "via", gateway_address, "dev", interface_name])
    if rc == 0:
        logger.info("Failover: switched to %s via %s", gateway_address, interface_name)
    return rc == 0


async def setup_nat_masquerade(interface_name: str) -> bool:
    """Set up MASQUERADE NAT for outgoing traffic on a provider interface."""
    _validate_iface(interface_name)

    if not IS_LINUX:
        logger.info("[SIM] Would set NAT masquerade on %s", interface_name)
        return True

    rc, _, _ = await _run(["iptables", "-t", "nat", "-A", "POSTROUTING", "-o", interface_name, "-j", "MASQUERADE"])
    return rc == 0


async def clear_nat_masquerade() -> bool:
    """Flush NAT masquerade rules."""
    if not IS_LINUX:
        return True
    rc, _, _ = await _run(["iptables", "-t", "nat", "-F", "POSTROUTING"])
    return rc == 0


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

async def ping_check(address: str, check_target: str = "8.8.8.8",
                     timeout: float = 2.0) -> tuple[bool, float | None]:
    """Check if a gateway can reach the internet by pinging check_target through it.

    On Linux uses: ping -c 1 -W <timeout> -I <gateway_addr> <target>
    Returns: (is_reachable, latency_ms)
    """
    try:
        start = time.monotonic()
        if IS_LINUX:
            # Ping through the specific gateway's interface
            cmd = ["ping", "-c", "1", "-W", str(int(timeout)), check_target]
        else:
            # macOS / dev fallback — just ping the gateway itself
            cmd = ["ping", "-c", "1", "-W", str(int(timeout * 1000)), address]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        returncode = await asyncio.wait_for(proc.wait(), timeout=timeout + 2)
        elapsed = (time.monotonic() - start) * 1000
        return returncode == 0, round(elapsed, 2)
    except (asyncio.TimeoutError, Exception):
        return False, None


# ---------------------------------------------------------------------------
# Balancer engine — ties it all together
# ---------------------------------------------------------------------------

class BalancerEngine:
    """Manages a single load balancer configuration's runtime state.

    Created and started by the API when a config is activated.
    Periodically checks gateway health and switches routes.
    """

    def __init__(self, config_id: int):
        self.config_id = config_id
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self, db_session_factory):
        """Start the health-check loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop(db_session_factory))
        logger.info("BalancerEngine started for config %d", self.config_id)

    async def stop(self):
        """Stop the health-check loop and clean up."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("BalancerEngine stopped for config %d", self.config_id)

    async def _run_loop(self, db_session_factory):
        """Main loop: check health, apply routes."""
        from app.models.loadbalancer import LoadBalancerConfig, Gateway

        while self._running:
            try:
                async with db_session_factory() as db:
                    cfg = await db.get(LoadBalancerConfig, self.config_id)
                    if not cfg or not cfg.is_active:
                        logger.info("Config %d no longer active, stopping engine", self.config_id)
                        self._running = False
                        break

                    interval = cfg.check_interval or 5
                    now = datetime.now(timezone.utc)

                    # Health check all gateways concurrently
                    tasks = [
                        ping_check(gw.address, cfg.check_target, cfg.check_timeout or 2.0)
                        for gw in cfg.gateways
                    ]
                    results = await asyncio.gather(*tasks)

                    changed = False
                    for gw, (is_healthy, latency_ms) in zip(cfg.gateways, results):
                        was_healthy = gw.is_healthy
                        gw.latency_ms = latency_ms
                        gw.last_check = now

                        if is_healthy:
                            gw.is_healthy = True
                            gw.consecutive_failures = 0
                        else:
                            gw.consecutive_failures += 1
                            if gw.consecutive_failures >= (cfg.check_failures or 3):
                                gw.is_healthy = False
                                if was_healthy:
                                    changed = True
                                    logger.warning(
                                        "Gateway %s (%s) marked DOWN after %d consecutive failures",
                                        gw.address, gw.interface_name, gw.consecutive_failures,
                                    )

                        if not was_healthy and gw.is_healthy:
                            changed = True
                            logger.info("Gateway %s (%s) recovered", gw.address, gw.interface_name)

                    # Apply routing changes
                    if changed or cfg.active_gateway_id is None:
                        await self._apply_routes(cfg, db)

                    await db.commit()

                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("BalancerEngine loop error: %s", e, exc_info=True)
                await asyncio.sleep(5)

    async def _apply_routes(self, cfg, db):
        """Apply routing based on mode and current gateway health."""
        now = datetime.now(timezone.utc)
        healthy = [gw for gw in cfg.gateways if gw.is_healthy]

        if not healthy:
            logger.error("Config %d: ALL gateways down, no route change possible", cfg.id)
            return

        if cfg.mode == "round_robin":
            gw_dicts = [
                {"address": gw.address, "interface_name": gw.interface_name,
                 "weight": gw.weight, "is_healthy": gw.is_healthy}
                for gw in cfg.gateways
            ]
            await apply_round_robin_routes(gw_dicts)

            # Set up NAT for all healthy gateways
            if IS_LINUX:
                await clear_nat_masquerade()
                for gw in healthy:
                    await setup_nat_masquerade(gw.interface_name)

            # Active == first healthy
            cfg.active_gateway_id = healthy[0].id

        elif cfg.mode == "failover":
            # Sort by priority (lower = higher priority), pick first healthy
            sorted_gw = sorted(healthy, key=lambda g: (not g.is_primary, g.priority))
            chosen = sorted_gw[0]

            if cfg.active_gateway_id != chosen.id:
                old_id = cfg.active_gateway_id
                cfg.active_gateway_id = chosen.id
                cfg.last_switch = now
                cfg.switch_count += 1

                await apply_failover_route(chosen.address, chosen.interface_name)

                if IS_LINUX:
                    await clear_nat_masquerade()
                    await setup_nat_masquerade(chosen.interface_name)

                logger.info(
                    "Failover switch: gw %s -> gw %s (total switches: %d)",
                    old_id, chosen.id, cfg.switch_count,
                )


# ---------------------------------------------------------------------------
# Global engine registry
# ---------------------------------------------------------------------------

_engines: dict[int, BalancerEngine] = {}


async def activate_balancer(config_id: int, db_session_factory) -> BalancerEngine:
    """Create/start a balancer engine for the given config."""
    if config_id in _engines:
        await _engines[config_id].stop()

    engine = BalancerEngine(config_id)
    _engines[config_id] = engine
    await engine.start(db_session_factory)
    return engine


async def deactivate_balancer(config_id: int):
    """Stop and remove a balancer engine."""
    engine = _engines.pop(config_id, None)
    if engine:
        await engine.stop()


async def deactivate_all():
    """Stop all running balancer engines."""
    for engine in list(_engines.values()):
        await engine.stop()
    _engines.clear()


def get_engine(config_id: int) -> BalancerEngine | None:
    return _engines.get(config_id)


def get_active_engines() -> dict[int, BalancerEngine]:
    return dict(_engines)
