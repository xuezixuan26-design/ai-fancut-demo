import os
import json
import shlex
import shutil
import subprocess
from pathlib import Path

from app.config import settings
from app.utils.ffmpeg_utils import run_ffmpeg


def enhance_video(input_path: Path, output_path: Path, mode: str = "ffmpeg_hq", preset: str = "idol_stage_hq") -> dict:
    if not input_path.exists():
        raise FileNotFoundError(f"Input video not found: {input_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if mode == "topaz":
        return _enhance_with_topaz(input_path, output_path, preset)
    return _enhance_with_ffmpeg(input_path, output_path, preset)


def topaz_available() -> dict:
    template = os.getenv("TOPAZ_COMMAND_TEMPLATE")
    candidates = _topaz_candidates()
    found = [str(path) for path in candidates if path.exists()]
    model_assets = _topaz_model_assets()
    ready = bool(template or (found and model_assets))
    return {
        "available": ready,
        "detected": bool(found),
        "command_template_configured": bool(template),
        "detected_paths": found,
        "model_assets_found": [str(path) for path in model_assets[:8]],
        "hint": _topaz_hint(found, model_assets, template),
    }


def _enhance_with_topaz(input_path: Path, output_path: Path, preset: str) -> dict:
    template = os.getenv("TOPAZ_COMMAND_TEMPLATE")
    if template:
        command = template.format(input=str(input_path), output=str(output_path), preset=preset)
        proc = subprocess.run(shlex.split(command), capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr[-3000:] or "Topaz command failed")
        return {"mode": "topaz", "preset": preset, "command": command}

    topaz_ffmpeg = next((path for path in _topaz_candidates() if path.exists()), None)
    if not topaz_ffmpeg:
        raise RuntimeError(
            "Topaz Video AI was not detected. Install Topaz or set TOPAZ_COMMAND_TEMPLATE, then retry with mode=topaz."
        )

    # Topaz installations expose different model/filter names across versions.
    # This command is intentionally isolated from the normal render path so failures do not destroy the original output.
    proc = subprocess.run(
        [
            str(topaz_ffmpeg),
            "-y",
            "-i",
            str(input_path),
            "-vf",
            _topaz_filter_for_preset(preset, input_path),
            "-c:v",
            "h264_mf",
            "-b:v",
            "18M",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "copy",
            str(output_path),
        ],
        capture_output=True,
        text=True,
        cwd=str(topaz_ffmpeg.parent),
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-3000:] or "Topaz ffmpeg failed")
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("Topaz ffmpeg finished without producing a valid output file.")
    return {"mode": "topaz", "preset": preset, "command": str(topaz_ffmpeg)}


def _enhance_with_ffmpeg(input_path: Path, output_path: Path, preset: str) -> dict:
    filters = {
        "idol_stage_hq": (
            "hqdn3d=1.15:1.05:5.5:5.5,"
            "unsharp=5:5:0.72:3:3:0.35,"
            "eq=contrast=1.035:brightness=0.006:saturation=1.035"
        ),
        "soft_face_hq": (
            "hqdn3d=0.85:0.75:4.2:4.2,"
            "unsharp=3:3:0.35:3:3:0.18,"
            "eq=contrast=1.02:brightness=0.008:saturation=1.02"
        ),
        "sharp_stage_hq": (
            "hqdn3d=1.35:1.2:6.2:6.2,"
            "unsharp=7:7:0.9:5:5:0.45,"
            "eq=contrast=1.05:saturation=1.05"
        ),
    }.get(preset, "")
    if not filters:
        raise ValueError(f"Unknown enhancement preset: {preset}")

    run_ffmpeg(
        [
            "-i",
            str(input_path),
            "-vf",
            filters,
            "-c:v",
            "libx264",
            "-preset",
            "veryslow",
            "-crf",
            "12",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )
    return {"mode": "ffmpeg_hq", "preset": preset, "filters": filters}


def _topaz_candidates() -> list[Path]:
    paths = [
        shutil.which("topaz"),
        shutil.which("topaz-video-ai"),
        shutil.which("tvai"),
        r"D:\Program Files\Topaz Labs LLC\Topaz Video\ffmpeg.exe",
        r"D:\Program Files\Topaz Labs LLC\Topaz Video\tvai.exe",
        r"C:\Program Files\Topaz Labs LLC\Topaz Video AI\ffmpeg.exe",
        r"C:\Program Files\Topaz Labs LLC\Topaz Video AI\tvai.exe",
        r"C:\Program Files\Topaz Labs LLC\Topaz Video\ffmpeg.exe",
        r"C:\Program Files\Topaz Labs LLC\Topaz Video\tvai.exe",
    ]
    return [Path(path) for path in paths if path]


def _topaz_model_assets() -> list[Path]:
    model_dirs = [
        Path(os.getenv("PROGRAMDATA", r"C:\ProgramData")) / "Topaz Labs LLC" / "Topaz Video" / "models",
        Path(os.getenv("LOCALAPPDATA", "")) / "Topaz Labs LLC" / "Topaz Video" / "models",
        Path(os.getenv("APPDATA", "")) / "Topaz Labs LLC" / "Topaz Video" / "models",
    ]
    assets: list[Path] = []
    for model_dir in model_dirs:
        if not model_dir.exists():
            continue
        for pattern in ("*.tz", "*.onnx", "*.engine", "*.plan"):
            assets.extend(path for path in model_dir.rglob(pattern) if path.stat().st_size > 1_000_000)
    return assets


def _topaz_hint(found: list[str], model_assets: list[Path], template: str | None) -> str:
    if template:
        return "TOPAZ_COMMAND_TEMPLATE is configured."
    if not found:
        return "Topaz Video AI executable was not detected."
    if not model_assets:
        return "Topaz was detected, but model weights were not found. Open Topaz Video AI once and download/run the target model, or configure TOPAZ_COMMAND_TEMPLATE."
    return "Topaz Video AI is ready."


def _topaz_filter_for_preset(preset: str, input_path: Path) -> str:
    params = {
        "idol_stage_hq": {
            "model": "ahq-12",
            "noise": 0.12,
            "compression": 0.22,
            "details": 0.16,
            "blur": 0.06,
            "halo": 0.04,
        },
        "soft_face_hq": {
            "model": "ahq-12",
            "noise": 0.08,
            "compression": 0.18,
            "details": 0.08,
            "blur": 0.02,
            "halo": 0.05,
        },
        "sharp_stage_hq": {
            "model": "ahq-12",
            "noise": 0.14,
            "compression": 0.26,
            "details": 0.2,
            "blur": 0.1,
            "halo": 0.04,
        },
    }.get(preset, {})
    model = params.get("model", "ahq-12")
    width, height = _probe_video_size(input_path)
    return (
        f"tvai_up=model={model}:scale=1:w={width}:h={height}:"
        "device=-2:download=1:"
        f"noise={params.get('noise', 0.1)}:"
        f"compression={params.get('compression', 0.2)}:"
        f"details={params.get('details', 0.12)}:"
        f"blur={params.get('blur', 0.04)}:"
        f"halo={params.get('halo', 0.04)}"
    )


def _probe_video_size(input_path: Path) -> tuple[int, int]:
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "json",
            str(input_path),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        try:
            stream = (json.loads(proc.stdout).get("streams") or [{}])[0]
            width = int(stream.get("width") or 0)
            height = int(stream.get("height") or 0)
            if width > 0 and height > 0:
                return width, height
        except (ValueError, TypeError, IndexError):
            pass
    return int(settings.output_width), int(settings.output_height)
