import shutil
import subprocess
from pathlib import Path


def ffmpeg_binary() -> str:
    binary = shutil.which("ffmpeg")
    if binary:
        return binary
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:
        raise RuntimeError("FFmpeg is not installed or not available in PATH.") from exc


def require_ffmpeg() -> str:
    return ffmpeg_binary()


def run_ffmpeg(args: list[str], timeout: int | None = None) -> None:
    try:
        proc = subprocess.run([require_ffmpeg(), "-y", *args], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"FFmpeg timed out after {timeout}s") from exc
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-3000:] or "FFmpeg failed")


def ffmpeg_escape_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace(":", "\\:")
