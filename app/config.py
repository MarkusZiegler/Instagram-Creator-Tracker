from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./data/insta_tracker.db"
    SECRET_KEY: str = "dev-secret-change-in-production"

    INSTAGRAM_USERNAME: Optional[str] = None
    INSTAGRAM_PASSWORD: Optional[str] = None
    INSTAGRAM_SESSION_FILE: str = "./data/ig_session"

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    NOTIFY_EMAIL: Optional[str] = None

    MORNING_CHECK_HOUR: int = 7
    MORNING_CHECK_MINUTE: int = 0
    TIMEZONE: str = "Europe/Vienna"

    DELAY_BETWEEN_CREATORS_MIN: float = 3.0
    DELAY_BETWEEN_CREATORS_MAX: float = 8.0
    MAX_POSTS_PER_CREATOR_PER_CHECK: int = 12

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
