from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    SECRET_KEY: str = "change-me-in-production-please"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24
    DB_URL: str = f"sqlite+aiosqlite:///{Path(__file__).parent.parent / 'blackwall.db'}"
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    class Config:
        env_prefix = "BLACKWALL_"

settings = Settings()
