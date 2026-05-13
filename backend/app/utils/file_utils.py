import shutil
import uuid
from pathlib import Path
from fastapi import UploadFile

from app.config import settings

VIDEO_EXTS = {".mp4", ".mov", ".m4v"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac"}


def ensure_storage() -> None:
    for name in [
        "raw_videos",
        "bgm",
        "reference",
        "frames",
        "clips",
        "outputs",
        "projects",
    ]:
        (settings.storage_dir / name).mkdir(parents=True, exist_ok=True)


def new_project_id() -> str:
    return uuid.uuid4().hex[:12]


def safe_filename(name: str) -> str:
    clean = "".join(c for c in Path(name).name if c.isalnum() or c in "._- ")
    return clean.strip().replace(" ", "_") or f"upload_{uuid.uuid4().hex}"


def project_dir(project_id: str) -> Path:
    path = settings.storage_dir / "projects" / project_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def project_asset_dir(kind: str, project_id: str) -> Path:
    path = settings.storage_dir / kind / project_id
    path.mkdir(parents=True, exist_ok=True)
    return path


async def save_upload(upload: UploadFile, folder: Path, allowed_exts: set[str]) -> Path:
    ext = Path(upload.filename or "").suffix.lower()
    if ext not in allowed_exts:
        raise ValueError(f"Unsupported file type: {ext}")
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / f"{uuid.uuid4().hex[:8]}_{safe_filename(upload.filename or 'file')}"
    with destination.open("wb") as out:
        shutil.copyfileobj(upload.file, out)
    return destination
