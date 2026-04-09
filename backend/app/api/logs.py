"""Logs: recent activity feed and search/filter."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.log import LogResponse, RecentActivityItem
from app.crud.log import crud_log

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("/recent", response_model=list[RecentActivityItem])
async def recent_activity(
    limit: int = Query(default=8, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Dashboard widget: recent firewall events formatted for the activity feed."""
    rows = await crud_log.get_recent(db, limit=limit)
    items = []
    for row in rows:
        ts = row.timestamp
        time_str = ts.strftime("%H:%M:%S") if ts else ""
        source = row.source_ip or "system"
        items.append(
            RecentActivityItem(
                id=str(row.id),
                time=time_str,
                action=row.action,
                source=source,
                message=row.message,
            )
        )
    return items


@router.get("", response_model=list[LogResponse])
async def list_logs(
    action: str | None = None,
    source_ip: str | None = None,
    skip: int = 0,
    limit: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Full log listing with optional filters."""
    if source_ip:
        return await crud_log.get_by_source_ip(db, source_ip, skip=skip, limit=limit)
    if action:
        return await crud_log.get_by_action(db, action, skip=skip, limit=limit)
    return await crud_log.get_all(db, skip=skip, limit=limit)
