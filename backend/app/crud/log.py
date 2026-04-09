"""Firewall log queries."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.log import FirewallLog


class CRUDLog(CRUDBase[FirewallLog]):
    async def get_recent(
        self, db: AsyncSession, limit: int = 8
    ) -> list[FirewallLog]:
        """Return most recent log entries, newest first."""
        result = await db.execute(
            select(self.model)
            .order_by(self.model.timestamp.desc())
            .limit(min(limit, 100))
        )
        return list(result.scalars().all())

    async def get_by_action(
        self, db: AsyncSession, action: str, skip: int = 0, limit: int = 50
    ) -> list[FirewallLog]:
        result = await db.execute(
            select(self.model)
            .where(self.model.action == action)
            .order_by(self.model.timestamp.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_source_ip(
        self, db: AsyncSession, source_ip: str, skip: int = 0, limit: int = 50
    ) -> list[FirewallLog]:
        result = await db.execute(
            select(self.model)
            .where(self.model.source_ip == source_ip)
            .order_by(self.model.timestamp.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())


crud_log = CRUDLog(FirewallLog)
