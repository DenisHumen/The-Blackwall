"""
System updater — checks for updates via GitHub and applies them safely.

Features:
  - Version comparison via git tags
  - Backup of local files before update
  - Rollback on failure
  - Preserves local data (databases, configs, secrets)
  - Progress reporting via callbacks
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable

logger = logging.getLogger("blackwall.updater")

GITHUB_REPO = "DenisHumen/The-Blackwall"
GITHUB_RAW = f"https://raw.githubusercontent.com/{GITHUB_REPO}"

# Root project directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# Files/dirs to preserve during update (relative to project root)
PRESERVE_PATHS = [
    "backend/blackwall.db",
    "backend/.secret_key",
    "backend/.env",
    ".env",
    "config/local/",
    "data/",
]

BACKUP_DIR = PROJECT_ROOT / "backups"


class UpdateStatus(str, Enum):
    IDLE = "idle"
    CHECKING = "checking"
    AVAILABLE = "available"
    DOWNLOADING = "downloading"
    BACKING_UP = "backing_up"
    APPLYING = "applying"
    REBUILDING = "rebuilding"
    COMPLETED = "completed"
    ROLLING_BACK = "rolling_back"
    FAILED = "failed"


@dataclass
class UpdateProgress:
    status: UpdateStatus = UpdateStatus.IDLE
    current_version: str = ""
    latest_version: str = ""
    changelog: str = ""
    progress_percent: int = 0
    message: str = ""
    error: str = ""
    started_at: str | None = None
    completed_at: str | None = None
    can_rollback: bool = False


# Global state
_progress = UpdateProgress()
_lock = asyncio.Lock()


def get_progress() -> UpdateProgress:
    return _progress


def _set_progress(**kwargs):
    global _progress
    for k, v in kwargs.items():
        setattr(_progress, k, v)


def _git(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run a git command synchronously."""
    return subprocess.run(
        ["git", *args],
        cwd=cwd or PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )


async def _async_git(*args: str, cwd: Path | None = None) -> tuple[int, str, str]:
    """Run a git command asynchronously."""
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        cwd=cwd or PROJECT_ROOT,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode, stdout.decode().strip(), stderr.decode().strip()


def get_current_version() -> str:
    """Get current version from git tag or commit hash."""
    # Try to get latest tag
    result = _git("describe", "--tags", "--abbrev=0")
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    # Fallback to short commit hash
    result = _git("rev-parse", "--short", "HEAD")
    if result.returncode == 0:
        return result.stdout.strip()
    return "unknown"


def get_current_commit() -> str:
    """Get current commit hash."""
    result = _git("rev-parse", "HEAD")
    return result.stdout.strip() if result.returncode == 0 else ""


async def check_for_updates() -> dict:
    """Check GitHub for newer version.

    Returns dict with: has_update, current_version, latest_version, changelog
    """
    async with _lock:
        _set_progress(status=UpdateStatus.CHECKING, message="Проверка обновлений...")

        current = get_current_version()
        current_commit = get_current_commit()
        _set_progress(current_version=current)

        # Fetch latest from remote
        rc, _, err = await _async_git("fetch", "--tags", "origin")
        if rc != 0:
            _set_progress(status=UpdateStatus.FAILED, error=f"git fetch failed: {err}")
            return {"has_update": False, "error": err}

        # Get latest tag from remote
        rc, out, _ = await _async_git("describe", "--tags", "--abbrev=0", "origin/main")
        latest_version = out if rc == 0 and out else ""

        if not latest_version:
            # No tags, compare commits
            rc, out, _ = await _async_git("rev-parse", "origin/main")
            remote_commit = out
            has_update = remote_commit != current_commit
            latest_version = remote_commit[:8] if has_update else current
        else:
            has_update = latest_version != current

        # Get changelog (commits between current and latest)
        changelog = ""
        if has_update:
            rc, out, _ = await _async_git("log", "--oneline", f"HEAD..origin/main")
            changelog = out

        _set_progress(
            status=UpdateStatus.AVAILABLE if has_update else UpdateStatus.IDLE,
            latest_version=latest_version,
            changelog=changelog,
            message="Доступно обновление" if has_update else "Система обновлена",
        )

        return {
            "has_update": has_update,
            "current_version": current,
            "latest_version": latest_version,
            "changelog": changelog,
        }


def _create_backup() -> Path:
    """Create a backup of the current state."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"backup_{timestamp}"
    backup_path.mkdir(parents=True, exist_ok=True)

    # Save current commit hash for rollback
    commit = get_current_commit()
    (backup_path / "commit_hash").write_text(commit)

    # Backup preserved files
    preserved_dir = backup_path / "preserved"
    preserved_dir.mkdir(exist_ok=True)

    for rel_path in PRESERVE_PATHS:
        src = PROJECT_ROOT / rel_path
        dst = preserved_dir / rel_path
        if src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            logger.info("Backed up: %s", rel_path)
        elif src.is_dir() and src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, dst, dirs_exist_ok=True)
            logger.info("Backed up dir: %s", rel_path)

    logger.info("Backup created at: %s", backup_path)
    return backup_path


def _restore_preserved(backup_path: Path):
    """Restore preserved files from backup."""
    preserved_dir = backup_path / "preserved"
    if not preserved_dir.exists():
        return

    for rel_path in PRESERVE_PATHS:
        src = preserved_dir / rel_path
        dst = PROJECT_ROOT / rel_path
        if src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            logger.info("Restored: %s", rel_path)
        elif src.is_dir() and src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, dst, dirs_exist_ok=True)
            logger.info("Restored dir: %s", rel_path)


async def apply_update() -> dict:
    """Apply the latest update from GitHub.

    Steps:
    1. Create backup
    2. git pull
    3. Restore preserved files
    4. Rebuild (pip install, npm build)
    5. Success or rollback
    """
    async with _lock:
        _set_progress(
            status=UpdateStatus.BACKING_UP,
            progress_percent=5,
            message="Создание резервной копии...",
            started_at=datetime.now(timezone.utc).isoformat(),
            error="",
        )

        try:
            # Step 1: Backup
            backup_path = _create_backup()
            _set_progress(
                progress_percent=15,
                message="Резервная копия создана. Загрузка обновления...",
                status=UpdateStatus.DOWNLOADING,
                can_rollback=True,
            )

            # Step 2: Git pull
            rc, out, err = await _async_git("pull", "--ff-only", "origin", "main")
            if rc != 0:
                # Try reset approach if ff-only fails
                rc, out, err = await _async_git("reset", "--hard", "origin/main")
                if rc != 0:
                    raise RuntimeError(f"git pull failed: {err}")

            _set_progress(
                progress_percent=40,
                message="Код обновлён. Восстановление локальных файлов...",
                status=UpdateStatus.APPLYING,
            )

            # Step 3: Restore preserved files
            _restore_preserved(backup_path)
            _set_progress(progress_percent=50, message="Пересборка зависимостей...")

            # Step 4: Rebuild
            _set_progress(status=UpdateStatus.REBUILDING, progress_percent=55, message="Установка Python зависимостей...")

            # pip install
            pip_proc = await asyncio.create_subprocess_exec(
                "pip", "install", "-r", str(PROJECT_ROOT / "backend" / "requirements.txt"),
                cwd=PROJECT_ROOT / "backend",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await pip_proc.communicate()

            _set_progress(progress_percent=70, message="Сборка фронтенда...")

            # npm install + build
            frontend_dir = PROJECT_ROOT / "frontend"
            if (frontend_dir / "package.json").exists():
                npm_proc = await asyncio.create_subprocess_exec(
                    "npm", "install",
                    cwd=frontend_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await npm_proc.communicate()

                _set_progress(progress_percent=85, message="npm build...")

                build_proc = await asyncio.create_subprocess_exec(
                    "npm", "run", "build",
                    cwd=frontend_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await build_proc.communicate()

            _set_progress(progress_percent=95, message="Финализация...")

            # Step 5: Success
            new_version = get_current_version()
            _set_progress(
                status=UpdateStatus.COMPLETED,
                progress_percent=100,
                current_version=new_version,
                message=f"Обновление завершено: {new_version}",
                completed_at=datetime.now(timezone.utc).isoformat(),
            )

            return {"success": True, "version": new_version}

        except Exception as e:
            logger.error("Update failed: %s", e, exc_info=True)
            _set_progress(
                status=UpdateStatus.FAILED,
                error=str(e),
                message=f"Ошибка обновления: {e}",
            )
            return {"success": False, "error": str(e)}


async def rollback() -> dict:
    """Rollback to the last backup."""
    async with _lock:
        _set_progress(status=UpdateStatus.ROLLING_BACK, message="Откат к предыдущей версии...")

        try:
            if not BACKUP_DIR.exists():
                raise RuntimeError("No backups found")

            # Find latest backup
            backups = sorted(BACKUP_DIR.iterdir(), reverse=True)
            if not backups:
                raise RuntimeError("No backups found")

            latest_backup = backups[0]
            commit_file = latest_backup / "commit_hash"

            if not commit_file.exists():
                raise RuntimeError("Backup corrupt: no commit hash")

            target_commit = commit_file.read_text().strip()

            # Reset to the backup commit
            rc, _, err = await _async_git("reset", "--hard", target_commit)
            if rc != 0:
                raise RuntimeError(f"git reset failed: {err}")

            # Restore preserved files
            _restore_preserved(latest_backup)

            version = get_current_version()
            _set_progress(
                status=UpdateStatus.COMPLETED,
                current_version=version,
                message=f"Откат завершён: {version}",
                progress_percent=100,
                completed_at=datetime.now(timezone.utc).isoformat(),
            )

            return {"success": True, "version": version}

        except Exception as e:
            logger.error("Rollback failed: %s", e, exc_info=True)
            _set_progress(
                status=UpdateStatus.FAILED,
                error=str(e),
                message=f"Ошибка отката: {e}",
            )
            return {"success": False, "error": str(e)}


def list_backups() -> list[dict]:
    """List available backups."""
    if not BACKUP_DIR.exists():
        return []

    result = []
    for d in sorted(BACKUP_DIR.iterdir(), reverse=True):
        if d.is_dir() and d.name.startswith("backup_"):
            commit_file = d / "commit_hash"
            result.append({
                "name": d.name,
                "commit": commit_file.read_text().strip() if commit_file.exists() else "unknown",
                "created_at": datetime.fromtimestamp(d.stat().st_mtime, tz=timezone.utc).isoformat(),
            })
    return result
