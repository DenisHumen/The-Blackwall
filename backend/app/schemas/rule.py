"""RuleCreate, RuleUpdate, RuleResponse, RuleStats"""

from pydantic import BaseModel, ConfigDict
from datetime import datetime


class RuleBase(BaseModel):
    name: str
    description: str = ""
    source_ip: str = ""
    dest_ip: str = ""
    source_port: str = ""
    dest_port: str = ""
    protocol: str = "any"
    interface: str = ""
    direction: str = "in"
    action: str = "drop"
    rate_limit: str = ""
    priority: int = 100
    is_active: bool = True


class RuleCreate(RuleBase):
    pass


class RuleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    source_ip: str | None = None
    dest_ip: str | None = None
    source_port: str | None = None
    dest_port: str | None = None
    protocol: str | None = None
    interface: str | None = None
    direction: str | None = None
    action: str | None = None
    rate_limit: str | None = None
    priority: int | None = None
    is_active: bool | None = None


class RuleResponse(RuleBase):
    id: int
    is_system: bool
    created_at: datetime
    updated_at: datetime
    created_by: str

    model_config = ConfigDict(from_attributes=True)


class RuleStats(BaseModel):
    """Dashboard widget: firewall rule statistics."""
    totalRules: int
    activeRules: int
    blockedToday: int
    threatsDetected: int
    lastThreat: str | None
