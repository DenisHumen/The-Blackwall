from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.database import init_db, SessionLocal

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Reconnect active balancers (skip in test mode)
    if not settings.TESTING:
        from app.core.loadbalancer import activate_balancer, deactivate_all
        from app.models.loadbalancer import LoadBalancerConfig
        from sqlalchemy import select
        try:
            async with SessionLocal() as db:
                result = await db.execute(
                    select(LoadBalancerConfig).where(LoadBalancerConfig.is_active.is_(True))
                )
                for cfg in result.scalars():
                    await activate_balancer(cfg.id, SessionLocal)
        except Exception:
            pass  # DB may not have tables yet
    yield
    if not settings.TESTING:
        from app.core.loadbalancer import deactivate_all
        await deactivate_all()

app = FastAPI(title="The Blackwall", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Routers ---
from app.api.auth import router as auth_router
from app.api.metrics import router as metrics_router
from app.api.loadbalancer import router as lb_router
from app.api.updater import router as updater_router
from app.api.rules import router as rules_router
from app.api.logs import router as logs_router

app.include_router(auth_router)
app.include_router(metrics_router)
app.include_router(lb_router)
app.include_router(updater_router)
app.include_router(rules_router)
app.include_router(logs_router)


# --- SPA static serving (production) ---
_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if _frontend_dist.is_dir():
    app.mount("/assets", StaticFiles(directory=_frontend_dist / "assets"), name="static-assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(request: Request, full_path: str):
        """Serve index.html for any non-API route (SPA routing)."""
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        file_path = _frontend_dist / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(_frontend_dist / "index.html")
else:
    @app.get("/")
    async def root():
        return {
            "name": "The Blackwall",
            "version": "0.1.0",
            "status": "running",
            "docs": "/docs",
            "message": "Frontend not built. Run: cd frontend && npm run build",
        }
