import secrets
from pydantic_settings import BaseSettings
from pathlib import Path

_BASE_DIR = Path(__file__).parent.parent
_SECRET_FILE = _BASE_DIR / ".secret_key"


def _load_or_generate_secret() -> str:
    """Load secret key from .secret_key file, or generate a new one."""
    if _SECRET_FILE.exists():
        key = _SECRET_FILE.read_text().strip()
        if key:
            return key
    key = secrets.token_urlsafe(64)
    _SECRET_FILE.write_text(key)
    _SECRET_FILE.chmod(0o600)
    return key


class Settings(BaseSettings):
    SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24
    DB_URL: str = f"sqlite+aiosqlite:///{_BASE_DIR / 'blackwall.db'}"
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
    TESTING: bool = False

    model_config = {"env_prefix": "BLACKWALL_"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.SECRET_KEY:
            self.SECRET_KEY = _load_or_generate_secret()

settings = Settings()
