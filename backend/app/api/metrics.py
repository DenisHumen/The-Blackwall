"""Metrics: Aggregated system metrics and traffic charts data."""

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.metrics import collect_metrics
from app.database import get_db
from app.models.metric import TrafficMetric
from app.models.user import User
from app.schemas.metric import SystemMetrics, TrafficPoint

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

# Max age for stored metrics (31 days)
_MAX_AGE_DAYS = 31


@router.get("/current", response_model=SystemMetrics)
async def current_metrics(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get current system metrics and persist traffic point."""
    data = collect_metrics()

    # Persist the traffic point to DB
    point = TrafficMetric(
        timestamp=datetime.fromisoformat(data["timestamp"]),
        rx_rate=data["network_rx_rate"],
        tx_rate=data["network_tx_rate"],
        rx_bytes=data["network_rx_bytes"],
        tx_bytes=data["network_tx_bytes"],
    )
    db.add(point)

    # Cleanup old data (older than 31 days) — run occasionally
    import random
    if random.random() < 0.01:  # 1% of requests
        cutoff = datetime.now(timezone.utc) - timedelta(days=_MAX_AGE_DAYS)
        await db.execute(
            delete(TrafficMetric).where(TrafficMetric.timestamp < cutoff)
        )

    await db.commit()
    return SystemMetrics(**data)


@router.get("/traffic", response_model=list[TrafficPoint])
async def traffic_history(
    range: str = Query(default="1h", pattern="^(1h|24h|7d|30d)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get traffic history for a time range.

    Supported ranges: 1h, 24h, 7d, 30d.
    For longer ranges, data is downsampled to keep response size reasonable.
    """
    range_map = {
        "1h": timedelta(hours=1),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }
    delta = range_map[range]
    cutoff = datetime.now(timezone.utc) - delta

    result = await db.execute(
        select(TrafficMetric)
        .where(TrafficMetric.timestamp >= cutoff)
        .order_by(TrafficMetric.timestamp.asc())
    )
    rows = result.scalars().all()

    # Downsample for large ranges to keep ~300-500 points
    max_points = 500
    if len(rows) > max_points:
        step = len(rows) / max_points
        sampled = []
        i = 0.0
        while int(i) < len(rows):
            sampled.append(rows[int(i)])
            i += step
        rows = sampled

    return [
        TrafficPoint(
            timestamp=r.timestamp,
            rx_rate=r.rx_rate,
            tx_rate=r.tx_rate,
        )
        for r in rows
    ]
