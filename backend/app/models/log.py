"""FirewallLog model — stores firewall events and system logs."""

from sqlalchemy import Column, Integer, String, DateTime, Index, func
from app.database import Base


class FirewallLog(Base):
    __tablename__ = "firewall_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, server_default=func.now(), index=True)

    # Event classification
    action = Column(String(20), nullable=False, default="block")   # block, allow, alert, system
    severity = Column(String(20), nullable=False, default="info")   # info, warning, critical

    # Source / destination
    source_ip = Column(String(100), nullable=True, default="")
    dest_ip = Column(String(100), nullable=True, default="")
    source_port = Column(Integer, nullable=True)
    dest_port = Column(Integer, nullable=True)
    protocol = Column(String(20), nullable=True, default="")

    # Details
    message = Column(String(500), nullable=False, default="")
    rule_id = Column(Integer, nullable=True)                       # which rule triggered this
    interface = Column(String(50), nullable=True, default="")
    bytes_count = Column(Integer, nullable=True, default=0)
    country_code = Column(String(10), nullable=True, default="")   # GeoIP

    __table_args__ = (
        Index("ix_firewall_logs_action_ts", "action", timestamp.desc()),
        Index("ix_firewall_logs_source", "source_ip", timestamp.desc()),
    )
