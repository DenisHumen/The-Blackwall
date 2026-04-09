"""FirewallRule model"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from app.database import Base


class FirewallRule(Base):
    __tablename__ = "firewall_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True, default="")

    # Rule matching
    source_ip = Column(String(100), nullable=True, default="")       # CIDR or IP
    dest_ip = Column(String(100), nullable=True, default="")         # CIDR or IP
    source_port = Column(String(50), nullable=True, default="")      # e.g. "80", "1024-65535"
    dest_port = Column(String(50), nullable=True, default="")        # e.g. "443"
    protocol = Column(String(20), nullable=True, default="any")      # tcp, udp, icmp, any
    interface = Column(String(50), nullable=True, default="")        # eth0, etc.
    direction = Column(String(10), nullable=False, default="in")     # in, out, forward

    # Action
    action = Column(String(20), nullable=False, default="drop")      # accept, drop, reject
    rate_limit = Column(String(50), nullable=True, default="")       # e.g. "100/minute"

    # Metadata
    priority = Column(Integer, nullable=False, default=100)          # lower = higher priority
    is_active = Column(Boolean, default=True)
    is_system = Column(Boolean, default=False)                       # system rules can't be deleted

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50), nullable=True, default="")
