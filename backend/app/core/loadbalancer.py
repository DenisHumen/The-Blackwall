"""
Load Balancer networking service.

This node acts as the main gateway for the local network (e.g. 10.0.0.123).
Traffic from LAN clients is forwarded through upstream gateways (routers/switches).

Supported modes:
  - Failover: primary upstream gateway with automatic switchover to backup
  - Round-robin: distribute traffic across multiple upstreams with weights

On Linux (production):
  - Enables IP forwarding so this node acts as a router
  - Manages default route to point to the active upstream gateway
  - Sets up NAT masquerade for outgoing traffic
  - Auto-detects outgoing interface via 'ip route get'
  - Optional: creates dummy interfaces for virtual gateway IP

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
# Saved routing state — used to restore networking on deactivation and to
# keep upstream gateways reachable after the default route is replaced.
# ---------------------------------------------------------------------------

_saved_default_route: dict | None = None  # {"gateway": str, "interface": str}
_installed_host_routes: list[dict] = []   # [{"address": str, "via": str}]

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
# Interface auto-detection
# ---------------------------------------------------------------------------

async def detect_interface(gateway_ip: str) -> str | None:
    """Auto-detect the outgoing interface for a given gateway IP.

    Uses 'ip route get <ip>' to determine which interface the kernel
    would use to reach that gateway.
    Returns interface name or None if detection fails.
    """
    _validate_ip(gateway_ip)

    if not IS_LINUX:
        logger.info("[SIM] Would detect interface for %s", gateway_ip)
        return "sim0"

    rc, out, _ = await _run(["ip", "route", "get", gateway_ip], check=False)
    if rc != 0:
        logger.warning("Cannot detect interface for %s", gateway_ip)
        return None

    # Parse output like: "10.0.1.1 via 10.0.0.1 dev ens18 src 10.0.0.123 uid 0"
    # or: "10.0.0.2 dev ens18 src 10.0.0.123 uid 0"
    match = re.search(r"\bdev\s+(\S+)", out)
    if match:
        iface = match.group(1)
        logger.debug("Detected interface %s for gateway %s", iface, gateway_ip)
        return iface

    logger.warning("Could not parse interface from: %s", out)
    return None


async def enable_ip_forwarding() -> bool:
    """Enable IPv4 forwarding so this node can act as a gateway/router."""
    if not IS_LINUX:
        logger.info("[SIM] Would enable IP forwarding")
        return True

    rc, _, _ = await _run(["sysctl", "-w", "net.ipv4.ip_forward=1"])
    if rc == 0:
        logger.info("IP forwarding enabled")
    return rc == 0


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
# Original route management — save/restore default route
# ---------------------------------------------------------------------------

async def get_default_route() -> dict | None:
    """Parse the current default route from the kernel routing table.

    Returns {"gateway": "x.x.x.x", "interface": "ethX"} or None.
    """
    if not IS_LINUX:
        logger.info("[SIM] Would read default route")
        return {"gateway": "10.0.0.1", "interface": "sim0"}

    rc, out, _ = await _run(["ip", "route", "show", "default"], check=False)
    if rc != 0 or not out:
        return None

    # Parse: "default via 10.0.0.1 dev ens18 proto static metric 100"
    gw_match = re.search(r"\bvia\s+(\S+)", out)
    dev_match = re.search(r"\bdev\s+(\S+)", out)
    if not gw_match:
        return None

    return {
        "gateway": gw_match.group(1),
        "interface": dev_match.group(1) if dev_match else "",
    }


async def save_original_route() -> dict | None:
    """Save the current default route so it can be restored later.

    Called once before the balancer first modifies the default route.
    Subsequent calls are no-ops (preserves the very first route).
    """
    global _saved_default_route
    if _saved_default_route is not None:
        return _saved_default_route

    route = await get_default_route()
    if route:
        _saved_default_route = route
        logger.info("Saved original default route: via %s dev %s",
                    route["gateway"], route["interface"])
    return route


async def restore_original_route() -> bool:
    """Restore the default route that was saved before the balancer started.

    Also removes any host routes that were added for upstream gateways.
    """
    global _saved_default_route, _installed_host_routes

    if not IS_LINUX:
        logger.info("[SIM] Would restore original route")
        _saved_default_route = None
        _installed_host_routes.clear()
        return True

    ok = True

    # 1. Restore default route
    if _saved_default_route:
        gw = _saved_default_route["gateway"]
        iface = _saved_default_route["interface"]
        _validate_ip(gw)
        if iface:
            _validate_iface(iface)
            rc, _, _ = await _run(
                ["ip", "route", "replace", "default", "via", gw, "dev", iface])
        else:
            rc, _, _ = await _run(
                ["ip", "route", "replace", "default", "via", gw])
        if rc == 0:
            logger.info("Restored original default route: via %s dev %s", gw, iface)
        else:
            ok = False
    else:
        logger.warning("No saved default route to restore")

    # 2. Remove host routes added for upstream gateways
    for hr in _installed_host_routes:
        await _run(["ip", "route", "del", f"{hr['address']}/32"], check=False)
        logger.debug("Removed host route for %s", hr["address"])
    _installed_host_routes.clear()

    _saved_default_route = None
    return ok


async def ensure_gateway_host_routes(gateway_addresses: list[str]) -> bool:
    """Add /32 host routes for each upstream gateway via the original default
    gateway.  This guarantees the node can always reach upstream gateways even
    after the default route is replaced.

    Only adds routes that don't already exist.
    """
    global _installed_host_routes

    if not _saved_default_route:
        logger.warning("Cannot add host routes: original route not saved")
        return False

    orig_gw = _saved_default_route["gateway"]
    orig_iface = _saved_default_route["interface"]

    if not IS_LINUX:
        for addr in gateway_addresses:
            logger.info("[SIM] Would add host route %s/32 via %s", addr, orig_gw)
            _installed_host_routes.append({"address": addr, "via": orig_gw})
        return True

    for addr in gateway_addresses:
        _validate_ip(addr)
        # Skip if this IS the original gateway (no route needed)
        if addr == orig_gw:
            continue
        # Skip if host route already installed
        if any(hr["address"] == addr for hr in _installed_host_routes):
            continue

        cmd = ["ip", "route", "replace", f"{addr}/32", "via", orig_gw]
        if orig_iface:
            _validate_iface(orig_iface)
            cmd += ["dev", orig_iface]
        rc, _, _ = await _run(cmd, check=False)
        if rc == 0:
            _installed_host_routes.append({"address": addr, "via": orig_gw})
            logger.info("Added host route: %s/32 via %s dev %s", addr, orig_gw, orig_iface)
        else:
            logger.warning("Failed to add host route for %s", addr)

    return True


# ---------------------------------------------------------------------------
# Routing management
# ---------------------------------------------------------------------------

async def apply_round_robin_routes(
    gateways: list[dict],
    virtual_subnet: str | None = None,
) -> bool:
    """Set up multipath routing with weights for round-robin balancing.

    gateways: [{"address": "10.0.1.1", "interface_name": "ens18", "weight": 2}, ...]
    interface_name is auto-detected if empty.
    """
    healthy = [g for g in gateways if g.get("is_healthy", True)]

    if not IS_LINUX:
        nexthops = " ".join(
            f"nexthop via {g['address']} weight {g.get('weight', 1)}"
            for g in healthy
        )
        logger.info("[SIM] Round-robin route: ip route replace default %s", nexthops)
        return True

    if not healthy:
        logger.warning("No healthy gateways for round-robin!")
        return False

    # Auto-detect interfaces for gateways that don't have one specified
    for g in healthy:
        if not g.get("interface_name"):
            detected = await detect_interface(g["address"])
            if detected:
                g["interface_name"] = detected
            else:
                logger.warning("Cannot detect interface for gateway %s, skipping", g["address"])
                continue

    healthy = [g for g in healthy if g.get("interface_name")]
    if not healthy:
        logger.warning("No gateways with resolvable interfaces!")
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
    interface_name: str = "",
) -> bool:
    """Switch the default route to the specified upstream gateway (failover mode).

    If interface_name is empty, it is auto-detected from the routing table.
    """
    _validate_ip(gateway_address)

    if not interface_name:
        interface_name = await detect_interface(gateway_address) or ""

    if not IS_LINUX:
        logger.info("[SIM] Failover route: via %s dev %s", gateway_address, interface_name or "auto")
        return True

    if interface_name:
        _validate_iface(interface_name)
        rc, _, _ = await _run(["ip", "route", "replace", "default", "via", gateway_address, "dev", interface_name])
    else:
        # Let kernel decide the interface
        rc, _, _ = await _run(["ip", "route", "replace", "default", "via", gateway_address])

    if rc == 0:
        logger.info("Failover: switched to %s via %s", gateway_address, interface_name or "auto")
    return rc == 0


async def setup_nat_masquerade(interface_name: str = "") -> bool:
    """Set up MASQUERADE NAT for outgoing traffic.

    If interface_name is empty, masquerade on all interfaces.
    """
    if not IS_LINUX:
        logger.info("[SIM] Would set NAT masquerade on %s", interface_name or "all")
        return True

    if interface_name:
        _validate_iface(interface_name)
        rc, _, _ = await _run(["iptables", "-t", "nat", "-A", "POSTROUTING", "-o", interface_name, "-j", "MASQUERADE"])
    else:
        rc, _, _ = await _run(["iptables", "-t", "nat", "-A", "POSTROUTING", "-j", "MASQUERADE"])
    return rc == 0


async def clear_nat_masquerade() -> bool:
    """Remove only masquerade rules added by the load balancer.

    Instead of flushing the entire POSTROUTING chain (which would destroy
    rules set by other subsystems), we delete only MASQUERADE rules.
    """
    if not IS_LINUX:
        return True

    # List rules with line numbers, then remove MASQUERADE ones in reverse
    rc, out, _ = await _run(
        ["iptables", "-t", "nat", "-L", "POSTROUTING", "--line-numbers", "-n"],
        check=False,
    )
    if rc != 0:
        return False

    lines_to_del: list[int] = []
    for line in out.splitlines():
        if "MASQUERADE" in line:
            parts = line.split()
            if parts and parts[0].isdigit():
                lines_to_del.append(int(parts[0]))

    # Delete in reverse order so line numbers stay valid
    for num in sorted(lines_to_del, reverse=True):
        await _run(
            ["iptables", "-t", "nat", "-D", "POSTROUTING", str(num)],
            check=False,
        )

    return True


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

async def ping_check(address: str, check_target: str = "8.8.8.8",
                     timeout: float = 2.0) -> tuple[bool, float | None]:
    """Check if an upstream gateway can reach the internet.

    First verifies the gateway itself is reachable (ping gateway),
    then checks internet connectivity through it by adding a temporary
    route for the check_target via this gateway.
    Returns: (is_reachable, latency_ms)
    """
    try:
        start = time.monotonic()

        if IS_LINUX:
            # Step 1: Check if the gateway itself is reachable
            cmd = ["ping", "-c", "1", "-W", str(int(timeout)), address]
        else:
            cmd = ["ping", "-c", "1", "-W", str(int(timeout * 1000)), address]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        returncode = await asyncio.wait_for(proc.wait(), timeout=timeout + 2)

        if returncode != 0:
            return False, None

        if IS_LINUX and check_target and check_target != address:
            # Step 2: Check internet through this specific gateway
            # Add a temporary host route for check_target via this gateway
            _validate_ip(address)
            _validate_ip(check_target)
            await _run(["ip", "route", "replace", f"{check_target}/32", "via", address], check=False)

            cmd2 = ["ping", "-c", "1", "-W", str(int(timeout)), check_target]
            proc2 = await asyncio.create_subprocess_exec(
                *cmd2,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            returncode = await asyncio.wait_for(proc2.wait(), timeout=timeout + 2)

            # Clean up temporary route
            await _run(["ip", "route", "del", f"{check_target}/32", "via", address], check=False)

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
        """Apply routing based on mode and current gateway health.

        Before replacing the default route, the original route is saved and
        host routes to all upstream gateways are installed so the node never
        loses the ability to reach them (and thus never loses internet).
        """
        now = datetime.now(timezone.utc)
        healthy = [gw for gw in cfg.gateways if gw.is_healthy]

        if not healthy:
            logger.error("Config %d: ALL gateways down, no route change possible", cfg.id)
            return

        # Enable IP forwarding so this node acts as a router
        await enable_ip_forwarding()

        # --- Preserve the node's own connectivity -----------------------
        # 1. Save the original default route (no-op after first call)
        await save_original_route()

        # 2. Ensure host routes exist for every upstream gateway so the
        #    node can reach them even after the default route changes.
        all_gw_addrs = [gw.address for gw in cfg.gateways]
        await ensure_gateway_host_routes(all_gw_addrs)
        # ----------------------------------------------------------------

        if cfg.mode == "round_robin":
            gw_dicts = [
                {"address": gw.address, "interface_name": gw.interface_name or "",
                 "weight": gw.weight, "is_healthy": gw.is_healthy}
                for gw in cfg.gateways
            ]
            await apply_round_robin_routes(gw_dicts)

            # Set up NAT masquerade
            if IS_LINUX:
                await clear_nat_masquerade()
                for gw in healthy:
                    iface = gw.interface_name or await detect_interface(gw.address) or ""
                    if iface:
                        await setup_nat_masquerade(iface)
                    else:
                        await setup_nat_masquerade()

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

                await apply_failover_route(chosen.address, chosen.interface_name or "")

                if IS_LINUX:
                    await clear_nat_masquerade()
                    iface = chosen.interface_name or await detect_interface(chosen.address) or ""
                    if iface:
                        await setup_nat_masquerade(iface)
                    else:
                        await setup_nat_masquerade()

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
    """Stop and remove a balancer engine, restoring original networking."""
    engine = _engines.pop(config_id, None)
    if engine:
        await engine.stop()
    # Restore the node's original default route and remove host routes
    await restore_original_route()
    # Clean up NAT masquerade rules added by the balancer
    await clear_nat_masquerade()
    logger.info("Balancer %d deactivated, original route restored", config_id)


async def deactivate_all():
    """Stop all running balancer engines."""
    for engine in list(_engines.values()):
        await engine.stop()
    _engines.clear()


def get_engine(config_id: int) -> BalancerEngine | None:
    return _engines.get(config_id)


def get_active_engines() -> dict[int, BalancerEngine]:
    return dict(_engines)
