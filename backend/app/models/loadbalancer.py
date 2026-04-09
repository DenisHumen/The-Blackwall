from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class LoadBalancerConfig(Base):
    __tablename__ = "lb_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    mode = Column(String(20), nullable=False, default="round_robin")  # round_robin | failover
    is_active = Column(Boolean, default=False)

    # Interface mode: if True, create a virtual dummy interface; if False, use system interfaces directly
    use_virtual_interface = Column(Boolean, default=False)
    virtual_ip = Column(String(50), nullable=False, default="")       # CIDR (only when use_virtual_interface=True)
    virtual_interface = Column(String(50), nullable=False, default="") # dummy iface name

    # Health-check settings
    check_interval = Column(Integer, default=5)         # seconds between checks
    check_target = Column(String(100), default="8.8.8.8")  # IP to ping for connectivity
    check_timeout = Column(Float, default=2.0)          # ping timeout in seconds
    check_failures = Column(Integer, default=3)         # failures before switching

    # Current state
    active_gateway_id = Column(Integer, ForeignKey("lb_gateways.id", ondelete="SET NULL", use_alter=True), nullable=True)
    last_switch = Column(DateTime, nullable=True)
    switch_count = Column(Integer, default=0)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    gateways = relationship("Gateway", back_populates="lb_config", cascade="all, delete-orphan",
                            lazy="selectin", foreign_keys="Gateway.lb_config_id")
    active_gateway = relationship("Gateway", foreign_keys=[active_gateway_id], post_update=True, lazy="selectin")


class Gateway(Base):
    __tablename__ = "lb_gateways"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lb_config_id = Column(Integer, ForeignKey("lb_configs.id", ondelete="CASCADE"), nullable=False)
    address = Column(String(100), nullable=False)        # Gateway IP, e.g. 192.168.1.1
    interface_name = Column(String(50), nullable=False)  # Physical iface: eth0, ens18
    weight = Column(Integer, default=1)                  # For round_robin
    priority = Column(Integer, default=1)                # For failover (lower = higher priority)
    is_primary = Column(Boolean, default=False)          # For failover mode
    is_healthy = Column(Boolean, default=True)
    last_check = Column(DateTime, nullable=True)
    latency_ms = Column(Float, nullable=True)
    consecutive_failures = Column(Integer, default=0)    # Current failure streak
    total_downtime_sec = Column(Float, default=0.0)      # Accumulated downtime

    lb_config = relationship("LoadBalancerConfig", back_populates="gateways", foreign_keys=[lb_config_id])
