"""LogSearch, LogResponse, LogExport, RecentActivityItem"""

from pydantic import BaseModel, ConfigDict
from datetime import datetime


class LogResponse(BaseModel):
    id: int
    timestamp: datetime
    action: str
    severity: str
    source_ip: str
    dest_ip: str
    source_port: int | None
    dest_port: int | None
    protocol: str
    message: str
    rule_id: int | None
    interface: str
    country_code: str

    model_config = ConfigDict(from_attributes=True)


class RecentActivityItem(BaseModel):
    """Dashboard widget: recent activity feed."""
    id: str
    time: str
    action: str       # block, allow, alert, system
    source: str
    message: str
