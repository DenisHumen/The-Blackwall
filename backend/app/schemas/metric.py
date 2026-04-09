from pydantic import BaseModel
from datetime import datetime


class SystemMetrics(BaseModel):
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    network_rx_bytes: int
    network_tx_bytes: int
    network_rx_rate: float
    network_tx_rate: float
    uptime_seconds: float
    load_avg_1: float
    load_avg_5: float
    load_avg_15: float
    timestamp: datetime


class TrafficPoint(BaseModel):
    timestamp: datetime
    rx_rate: float
    tx_rate: float
