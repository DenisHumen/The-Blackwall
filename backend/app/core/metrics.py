"""System metrics collector — cross-platform, uses /proc on Linux, psutil-like fallbacks on others."""

import os
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

_prev_net: dict[str, tuple[int, int, float]] = {}  # key -> (rx, tx, timestamp)
_traffic_history: list[dict] = []  # ring buffer
_MAX_TRAFFIC_HISTORY = 3600  # 1 hour at 1-second resolution


def _read_proc_stat_cpu() -> tuple[int, int] | None:
    """Read total and idle CPU jiffies from /proc/stat (Linux only)."""
    try:
        with open("/proc/stat") as f:
            line = f.readline()
        parts = line.split()
        values = [int(v) for v in parts[1:]]
        total = sum(values)
        idle = values[3] + (values[4] if len(values) > 4 else 0)
        return total, idle
    except Exception:
        return None


_prev_cpu: tuple[int, int] | None = None


def get_cpu_percent() -> float:
    """Get CPU usage percent."""
    global _prev_cpu

    if platform.system() == "Linux":
        cur = _read_proc_stat_cpu()
        if cur and _prev_cpu:
            d_total = cur[0] - _prev_cpu[0]
            d_idle = cur[1] - _prev_cpu[1]
            _prev_cpu = cur
            return max(0.0, (1 - d_idle / max(d_total, 1)) * 100)
        _prev_cpu = cur
        return 0.0
    else:
        # macOS/Windows fallback: use os.getloadavg or basic heuristic
        try:
            load = os.getloadavg()
            cpus = os.cpu_count() or 1
            return min(load[0] / cpus * 100, 100.0)
        except (OSError, AttributeError):
            return 0.0


def get_memory_info() -> tuple[float, float, float]:
    """Return (percent, used_mb, total_mb)."""
    if platform.system() == "Linux":
        try:
            info = {}
            with open("/proc/meminfo") as f:
                for line in f:
                    parts = line.split()
                    info[parts[0].rstrip(":")] = int(parts[1])
            total = info.get("MemTotal", 0)
            avail = info.get("MemAvailable", info.get("MemFree", 0))
            used = total - avail
            total_mb = total / 1024
            used_mb = used / 1024
            percent = (used / max(total, 1)) * 100
            return percent, used_mb, total_mb
        except Exception:
            pass

    # macOS fallback
    try:
        import subprocess
        result = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, timeout=2)
        total_bytes = int(result.stdout.strip())
        total_mb = total_bytes / (1024 * 1024)
        # Approximate used via vm_stat
        result2 = subprocess.run(["vm_stat"], capture_output=True, text=True, timeout=2)
        pages_free = 0
        page_size = 4096
        for line in result2.stdout.splitlines():
            if "page size" in line.lower():
                page_size = int(''.join(c for c in line if c.isdigit()) or 4096)
            if "Pages free" in line:
                pages_free = int(''.join(c for c in line.split(":")[1] if c.isdigit()))
            if "Pages speculative" in line:
                pages_free += int(''.join(c for c in line.split(":")[1] if c.isdigit()))
        free_mb = pages_free * page_size / (1024 * 1024)
        used_mb = total_mb - free_mb
        percent = (used_mb / max(total_mb, 1)) * 100
        return percent, used_mb, total_mb
    except Exception:
        return 0.0, 0.0, 0.0


def get_disk_info() -> tuple[float, float, float]:
    """Return (percent, used_gb, total_gb)."""
    try:
        stat = os.statvfs("/")
        total = stat.f_blocks * stat.f_frsize
        free = stat.f_bfree * stat.f_frsize
        used = total - free
        total_gb = total / (1024 ** 3)
        used_gb = used / (1024 ** 3)
        percent = (used / max(total, 1)) * 100
        return percent, used_gb, total_gb
    except Exception:
        return 0.0, 0.0, 0.0


def get_network_bytes() -> tuple[int, int]:
    """Return total (rx_bytes, tx_bytes)."""
    if platform.system() == "Linux":
        try:
            rx_total = tx_total = 0
            with open("/proc/net/dev") as f:
                for line in f:
                    if ":" not in line:
                        continue
                    iface, data = line.split(":")
                    iface = iface.strip()
                    if iface == "lo":
                        continue
                    parts = data.split()
                    rx_total += int(parts[0])
                    tx_total += int(parts[8])
            return rx_total, tx_total
        except Exception:
            pass

    # macOS fallback
    try:
        import subprocess
        result = subprocess.run(["netstat", "-ib"], capture_output=True, text=True, timeout=3)
        rx_total = tx_total = 0
        lines = result.stdout.strip().splitlines()
        if lines:
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 10 and parts[0] != "lo0" and parts[2] != "<Link#0>":
                    try:
                        rx_total += int(parts[6])
                        tx_total += int(parts[9])
                    except (ValueError, IndexError):
                        pass
        return rx_total, tx_total
    except Exception:
        return 0, 0


def get_load_avg() -> tuple[float, float, float]:
    """Return (1min, 5min, 15min) load averages."""
    try:
        load = os.getloadavg()
        return load[0], load[1], load[2]
    except (OSError, AttributeError):
        return 0.0, 0.0, 0.0


def get_uptime() -> float:
    """Return uptime in seconds."""
    if platform.system() == "Linux":
        try:
            with open("/proc/uptime") as f:
                return float(f.readline().split()[0])
        except Exception:
            pass

    # macOS fallback
    try:
        import subprocess
        result = subprocess.run(["sysctl", "-n", "kern.boottime"], capture_output=True, text=True, timeout=2)
        # Parse "{ sec = 1234567890, usec = 0 }"
        sec_str = result.stdout.split("sec =")[1].split(",")[0].strip()
        boot_time = int(sec_str)
        return time.time() - boot_time
    except Exception:
        return 0.0


def collect_metrics() -> dict:
    """Collect all system metrics and return as dict matching SystemMetrics schema."""
    global _prev_net

    now = time.time()
    now_dt = datetime.now(timezone.utc)

    cpu = get_cpu_percent()
    mem_pct, mem_used, mem_total = get_memory_info()
    disk_pct, disk_used, disk_total = get_disk_info()
    rx_bytes, tx_bytes = get_network_bytes()
    load1, load5, load15 = get_load_avg()
    uptime = get_uptime()

    # Calculate network rates
    prev = _prev_net.get("total")
    rx_rate = tx_rate = 0.0
    if prev:
        dt = max(now - prev[2], 0.1)
        rx_rate = max(0, (rx_bytes - prev[0]) / dt)
        tx_rate = max(0, (tx_bytes - prev[1]) / dt)
    _prev_net["total"] = (rx_bytes, tx_bytes, now)

    # Store in traffic history
    point = {"timestamp": now_dt.isoformat(), "rx_rate": rx_rate, "tx_rate": tx_rate}
    _traffic_history.append(point)
    if len(_traffic_history) > _MAX_TRAFFIC_HISTORY:
        _traffic_history.pop(0)

    return {
        "cpu_percent": round(cpu, 2),
        "memory_percent": round(mem_pct, 2),
        "memory_used_mb": round(mem_used, 2),
        "memory_total_mb": round(mem_total, 2),
        "disk_percent": round(disk_pct, 2),
        "disk_used_gb": round(disk_used, 2),
        "disk_total_gb": round(disk_total, 2),
        "network_rx_bytes": rx_bytes,
        "network_tx_bytes": tx_bytes,
        "network_rx_rate": round(rx_rate, 2),
        "network_tx_rate": round(tx_rate, 2),
        "uptime_seconds": round(uptime, 0),
        "load_avg_1": round(load1, 2),
        "load_avg_5": round(load5, 2),
        "load_avg_15": round(load15, 2),
        "timestamp": now_dt.isoformat(),
    }


def get_traffic_history(minutes: int = 60) -> list[dict]:
    """Return traffic history for the last N minutes."""
    cutoff = time.time() - minutes * 60
    return [
        p for p in _traffic_history
        if datetime.fromisoformat(p["timestamp"]).timestamp() > cutoff
    ]
