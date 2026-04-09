import time
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sa_func
from app.database import get_db
from app.models.user import User
from app.schemas.auth import SetupRequest, LoginRequest, UserResponse
from app.core.auth import hash_password, verify_password, create_jwt, get_current_user
from datetime import datetime, timezone

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Simple in-memory rate limiter for login — with max size cap
_login_attempts: dict[str, list[float]] = {}
_MAX_RATE_LIMIT_ENTRIES = 10000


def _check_rate_limit(ip: str, max_attempts: int = 5, window: int = 60):
    now = time.time()

    # Cleanup stale entries periodically to prevent memory leak
    if len(_login_attempts) > _MAX_RATE_LIMIT_ENTRIES:
        stale_keys = [k for k, v in _login_attempts.items()
                      if not v or now - v[-1] > window]
        for k in stale_keys:
            del _login_attempts[k]

    attempts = _login_attempts.get(ip, [])
    attempts = [t for t in attempts if now - t < window]
    _login_attempts[ip] = attempts
    if len(attempts) >= max_attempts:
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")
    attempts.append(now)
    _login_attempts[ip] = attempts


def _validate_password(password: str):
    """Validate password strength."""
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")


@router.post("/setup", response_model=UserResponse)
async def setup(req: SetupRequest, db: AsyncSession = Depends(get_db)):
    count = await db.scalar(select(sa_func.count()).select_from(User))
    if count > 0:
        raise HTTPException(status_code=400, detail="Setup already completed")
    _validate_password(req.password)
    user = User(username=req.username, password_hash=hash_password(req.password), role="root")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login")
async def login(req: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    _check_rate_limit(request.client.host if request.client else "unknown")
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user.last_login = datetime.now(timezone.utc)
    await db.commit()
    token = create_jwt(user.id, user.username)
    is_secure = request.url.scheme == "https"
    response.set_cookie(
        "access_token", token, httponly=True, samesite="lax",
        secure=is_secure, max_age=86400,
    )
    return {"message": "ok", "user": UserResponse.model_validate(user)}

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "ok"}

@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return user


@router.get("/setup-check")
async def setup_check(db: AsyncSession = Depends(get_db)):
    """Check if initial setup has been completed (any users exist)."""
    count = await db.scalar(select(sa_func.count()).select_from(User))
    return {"needs_setup": count == 0}
