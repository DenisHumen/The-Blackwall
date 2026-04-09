"""BlockedIP model — tracks blocked IP addresses."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from app.database import Base


class BlockedIP(Base):
    __tablename__ = "blocked_ips"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ip_address = Column(String(100), nullable=False, index=True)      # IP or CIDR
    reason = Column(String(500), nullable=False, default="")
    source = Column(String(50), nullable=False, default="manual")     # manual, autoblock, rule
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)                       # null = permanent
    blocked_at = Column(DateTime, server_default=func.now())
    created_by = Column(String(50), nullable=True, default="")
