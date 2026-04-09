"""Firewall rule CRUD operations."""

from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.rule import FirewallRule
from app.models.log import FirewallLog


class CRUDRule(CRUDBase[FirewallRule]):
    async def get_active(self, db: AsyncSession) -> list[FirewallRule]:
        result = await db.execute(
            select(self.model)
            .where(self.model.is_active.is_(True))
            .order_by(self.model.priority.asc())
        )
        return list(result.scalars().all())

    async def get_stats(self, db: AsyncSession) -> dict:
        """Aggregate statistics for the dashboard widget."""
        total = await db.scalar(
            select(func.count()).select_from(self.model)
        ) or 0
        active = await db.scalar(
            select(func.count()).select_from(self.model)
            .where(self.model.is_active.is_(True))
        ) or 0

        # Blocked today from logs
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        blocked_today = await db.scalar(
            select(func.count()).select_from(FirewallLog)
            .where(
                FirewallLog.action == "block",
                FirewallLog.timestamp >= today_start,
            )
        ) or 0

        # Threats = critical severity logs today
        threats = await db.scalar(
            select(func.count()).select_from(FirewallLog)
            .where(
                FirewallLog.severity == "critical",
                FirewallLog.timestamp >= today_start,
            )
        ) or 0

        # Last threat time
        last = await db.execute(
            select(FirewallLog.timestamp)
            .where(FirewallLog.severity == "critical")
            .order_by(FirewallLog.timestamp.desc())
            .limit(1)
        )
        last_row = last.scalar_one_or_none()
        last_threat = None
        if last_row:
            ts = last_row if last_row.tzinfo else last_row.replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - ts
            if delta < timedelta(minutes=1):
                last_threat = "только что"
            elif delta < timedelta(hours=1):
                last_threat = f"{int(delta.total_seconds() // 60)} мин назад"
            elif delta < timedelta(days=1):
                last_threat = f"{int(delta.total_seconds() // 3600)} ч назад"
            else:
                last_threat = f"{delta.days} д назад"

        return {
            "totalRules": total,
            "activeRules": active,
            "blockedToday": blocked_today,
            "threatsDetected": threats,
            "lastThreat": last_threat,
        }


crud_rule = CRUDRule(FirewallRule)
