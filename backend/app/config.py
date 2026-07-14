import os
from pathlib import Path

try:
    from pydantic_settings import BaseSettings
except Exception:
    BaseSettings = None


class _FallbackSettings:
    app_name: str = "AI Fancut Demo"
    api_prefix: str = "/api"
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    root_dir: Path = Path(__file__).resolve().parents[2]
    storage_dir: Path = root_dir / "storage"
    output_width: int = int(os.getenv("OUTPUT_WIDTH", "1080"))
    output_height: int = int(os.getenv("OUTPUT_HEIGHT", "1920"))
    output_fps: int = int(os.getenv("OUTPUT_FPS", "30"))
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "800"))


if BaseSettings is not None:

    class Settings(BaseSettings):
        app_name: str = "AI Fancut Demo"
        api_prefix: str = "/api"
        openai_api_key: str | None = None
        openai_model: str = "gpt-4o-mini"
        cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
        root_dir: Path = Path(__file__).resolve().parents[2]
        storage_dir: Path = root_dir / "storage"
        output_width: int = 1080
        output_height: int = 1920
        output_fps: int = 30
        max_upload_mb: int = 800

        class Config:
            env_file = ".env"
            extra = "ignore"

else:
    Settings = _FallbackSettings


settings = Settings()
