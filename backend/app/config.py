import os
from pathlib import Path

try:
    from pydantic_settings import BaseSettings
except Exception:
    BaseSettings = None


def _default_root_dir() -> Path:
    path = Path(__file__).resolve()
    if len(path.parents) > 2 and path.parents[1].name == "backend":
        return path.parents[2]
    return path.parents[1]


class _FallbackSettings:
    app_name: str = "AI Fancut Demo"
    api_prefix: str = "/api"
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    root_dir: Path = Path(os.getenv("ROOT_DIR", str(_default_root_dir())))
    storage_dir: Path = Path(os.getenv("STORAGE_DIR", str(_default_root_dir() / "storage")))
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
        cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
        root_dir: Path = _default_root_dir()
        storage_dir: Path = _default_root_dir() / "storage"
        output_width: int = 1080
        output_height: int = 1920
        output_fps: int = 30
        max_upload_mb: int = 800

        class Config:
            env_file = ".env"
            extra = "ignore"

else:
    Settings = _FallbackSettings


def _apply_runtime_env(settings_obj):
    raw_origins = os.getenv("CORS_ORIGINS") or settings_obj.cors_origins
    settings_obj.cors_origins = [origin.strip() for origin in str(raw_origins).split(",") if origin.strip()]
    return settings_obj


settings = _apply_runtime_env(Settings())
