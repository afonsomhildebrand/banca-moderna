from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

WEAK_SECRET_KEYS = {"", "troque-esta-chave"}


class Settings(BaseSettings):
    database_url: str = "mysql+pymysql://banca_user:banca_password@db:3306/banca_moderna"
    app_secret_key: str = "troque-esta-chave"
    secure_cookies: bool = False
    csrf_max_body_bytes: int = 64_000
    login_rate_limit_attempts: int = 5
    login_rate_limit_window_seconds: int = 300
    initial_admin_email: str | None = None
    initial_admin_password: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.app_secret_key in WEAK_SECRET_KEYS:
        raise RuntimeError("Defina APP_SECRET_KEY com um valor forte antes de iniciar a aplicacao.")
    return settings
