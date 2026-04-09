from pydantic import BaseModel, ConfigDict
from datetime import datetime


# --- Gateway ---

class GatewayBase(BaseModel):
    address: str
    interface_name: str
    weight: int = 1
    priority: int = 1
    is_primary: bool = False


class GatewayCreate(GatewayBase):
    pass


class GatewayResponse(GatewayBase):
    id: int
    lb_config_id: int
    is_healthy: bool
    last_check: datetime | None
    latency_ms: float | None
    consecutive_failures: int
    total_downtime_sec: float

    model_config = ConfigDict(from_attributes=True)


# --- LoadBalancer ---

class LoadBalancerBase(BaseModel):
    name: str
    mode: str = "round_robin"
    use_virtual_interface: bool = False
    virtual_ip: str = ""
    virtual_interface: str = ""
    check_interval: int = 5
    check_target: str = "8.8.8.8"
    check_timeout: float = 2.0
    check_failures: int = 3


class LoadBalancerCreate(LoadBalancerBase):
    gateways: list[GatewayCreate]


class LoadBalancerUpdate(BaseModel):
    name: str | None = None
    mode: str | None = None
    is_active: bool | None = None
    use_virtual_interface: bool | None = None
    virtual_ip: str | None = None
    virtual_interface: str | None = None
    check_interval: int | None = None
    check_target: str | None = None
    check_timeout: float | None = None
    check_failures: int | None = None


class LoadBalancerResponse(LoadBalancerBase):
    id: int
    is_active: bool
    active_gateway_id: int | None
    last_switch: datetime | None
    switch_count: int
    created_at: datetime
    updated_at: datetime
    gateways: list[GatewayResponse]

    model_config = ConfigDict(from_attributes=True)


class LoadBalancerStatus(BaseModel):
    """Runtime status returned by /status endpoint."""
    id: int
    name: str
    mode: str
    is_active: bool
    virtual_interface: str
    virtual_ip: str
    interface_exists: bool
    active_gateway: GatewayResponse | None
    gateways: list[GatewayResponse]
    switch_count: int
    last_switch: datetime | None
