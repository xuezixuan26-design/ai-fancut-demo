from pathlib import Path
from pydantic_settings import BaseSettings


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


settings = Settings()
