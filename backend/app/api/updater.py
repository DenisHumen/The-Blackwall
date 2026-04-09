"""Update management API — check, apply, rollback, status."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.auth import get_current_user
from app.models.user import User
from app.core.updater import (
    check_for_updates,
    apply_update,
    rollback,
    get_progress,
    list_backups,
    get_current_version,
    UpdateStatus,
)

router = APIRouter(prefix="/api/updater", tags=["updater"])


class UpdateCheckResponse(BaseModel):
    has_update: bool
    current_version: str = ""
    latest_version: str = ""
    changelog: str = ""
    error: str | None = None


class UpdateProgressResponse(BaseModel):
    status: str
    current_version: str
    latest_version: str
    changelog: str
    progress_percent: int
    message: str
    error: str
    started_at: str | None
    completed_at: str | None
    can_rollback: bool


class BackupInfo(BaseModel):
    name: str
    commit: str
    created_at: str


@router.get("/check", response_model=UpdateCheckResponse)
async def check(user: User = Depends(get_current_user)):
    """Check for available updates from GitHub."""
    result = await check_for_updates()
    return UpdateCheckResponse(**result)


@router.post("/apply")
async def do_update(user: User = Depends(get_current_user)):
    """Apply the latest update."""
    if user.role != "root":
        raise HTTPException(status_code=403, detail="Only root can apply updates")

    progress = get_progress()
    if progress.status in (UpdateStatus.DOWNLOADING, UpdateStatus.APPLYING,
                           UpdateStatus.REBUILDING, UpdateStatus.BACKING_UP):
        raise HTTPException(status_code=409, detail="Update already in progress")

    result = await apply_update()
    return result


@router.post("/rollback")
async def do_rollback(user: User = Depends(get_current_user)):
    """Rollback to the previous version."""
    if user.role != "root":
        raise HTTPException(status_code=403, detail="Only root can rollback")

    result = await rollback()
    return result


@router.get("/progress", response_model=UpdateProgressResponse)
async def progress(user: User = Depends(get_current_user)):
    """Get current update progress."""
    p = get_progress()
    return UpdateProgressResponse(
        status=p.status.value,
        current_version=p.current_version or get_current_version(),
        latest_version=p.latest_version,
        changelog=p.changelog,
        progress_percent=p.progress_percent,
        message=p.message,
        error=p.error,
        started_at=p.started_at,
        completed_at=p.completed_at,
        can_rollback=p.can_rollback,
    )


@router.get("/backups", response_model=list[BackupInfo])
async def get_backups(user: User = Depends(get_current_user)):
    """List available backups."""
    return [BackupInfo(**b) for b in list_backups()]
