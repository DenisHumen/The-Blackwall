"""BlockedIP CRUD operations."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.blocked_ip import BlockedIP


class CRUDBlockedIP(CRUDBase[BlockedIP]):
    async def get_active(self, db: AsyncSession) -> list[BlockedIP]:
        """Return currently active blocks (not expired)."""
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(self.model)
            .where(
                self.model.is_active.is_(True),
            )
            .order_by(self.model.blocked_at.desc())
        )
        rows = list(result.scalars().all())
        # Filter out expired in Python (sqlite lacks timezone-aware comparison)
        return [
            r for r in rows
            if r.expires_at is None or r.expires_at.replace(tzinfo=timezone.utc) > now
        ]

    async def find_by_ip(self, db: AsyncSession, ip: str) -> BlockedIP | None:
        result = await db.execute(
            select(self.model)
            .where(self.model.ip_address == ip, self.model.is_active.is_(True))
            .limit(1)
        )
        return result.scalar_one_or_none()


crud_blocked_ip = CRUDBlockedIP(BlockedIP)
