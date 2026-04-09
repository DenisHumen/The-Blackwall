"""TrafficMetric model — persistent traffic history."""

from sqlalchemy import Column, Integer, Float, DateTime, Index, func
from app.database import Base


class TrafficMetric(Base):
    __tablename__ = "traffic_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, server_default=func.now(), index=True)
    rx_rate = Column(Float, nullable=False, default=0.0)
    tx_rate = Column(Float, nullable=False, default=0.0)
    rx_bytes = Column(Integer, nullable=False, default=0)
    tx_bytes = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index("ix_traffic_metrics_ts_desc", timestamp.desc()),
    )
