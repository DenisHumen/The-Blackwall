"""BlockedIPCreate, BlockedIPResponse"""

from pydantic import BaseModel, ConfigDict
from datetime import datetime


class BlockedIPCreate(BaseModel):
    ip_address: str
    reason: str = ""
    source: str = "manual"
    expires_at: datetime | None = None


class BlockedIPResponse(BaseModel):
    id: int
    ip_address: str
    reason: str
    source: str
    is_active: bool
    expires_at: datetime | None
    blocked_at: datetime
    created_by: str

    model_config = ConfigDict(from_attributes=True)
