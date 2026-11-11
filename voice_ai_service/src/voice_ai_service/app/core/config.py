from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[4] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # PostgreSQL — база "conversation"
    DATABASE_URL: str = "postgresql+asyncpg://user:password@db:5432/conversation"

    gemini_api_key: str = "YOUR_GEMINI_API_KEY"
    gemini_model: str = "gemini-3.8-flash"
    gemini_tts_model: str = "gemini-3.8-flash-tts"
    tts_voice_uk: str = "Kore"
    tts_voice_en: str = "Kore"

    app_title: str = "Voice AI Interview Service"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"

    grpc_port: int = 50051
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"
    # False when the outbox relay runs as its own process (see voice_ai_service.relay).
    run_outbox_relay: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
