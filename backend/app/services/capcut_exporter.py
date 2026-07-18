from typing import Any

from app.config import settings
from app.models.schemas import ProjectState
from app.services.aspect_ratio import output_size
from app.utils.file_utils import project_asset_dir


def build_capcut_actions(state: ProjectState) -> dict[str, Any]:
    timeline = state.timeline or {}
    width, height = output_size(timeline.get("aspect_ratio") or state.aspect_ratio)
    items = timeline.get("timeline", [])
    warnings: list[str] = []
    actions: list[dict[str, Any]] = [
        {
            "action": "create_project",
            "params": {
                "name": f"{state.project_id}_fancut",
                "canvas": {"width": width, "height": height, "aspect_ratio": timeline.get("aspect_ratio") or state.aspect_ratio},
                "fps": settings.output_fps,
            },
        }
    ]

    raw_dir = project_asset_dir("raw_videos", state.project_id)
    bgm_dir = project_asset_dir("bgm", state.project_id)
    for name in state.videos:
        path = raw_dir / name
        exists = path.exists()
        if not exists:
            warnings.append(f"素材文件已清理或不存在：{name}")
        actions.append({"action": "import_media", "params": {"type": "video", "id": name, "path": str(path), "exists": exists}})
    if state.bgm:
        path = bgm_dir / state.bgm
        exists = path.exists()
        if not exists:
            warnings.append(f"BGM 文件已清理或不存在：{state.bgm}")
        actions.append({"action": "import_media", "params": {"type": "audio", "id": state.bgm, "path": str(path), "exists": exists}})

    cursor = 0.0
    for index, item in enumerate(items):
        duration = max(0.1, float(item.get("end", 0)) - float(item.get("start", 0))) / max(0.2, float(item.get("speed", 1.0)))
        actions.append(
            {
                "action": "add_video_clip",
                "params": {
                    "track": "main_video",
                    "clip_id": f"clip_{index + 1:03d}",
                    "media_id": item.get("source"),
                    "source_in": item.get("start"),
                    "source_out": item.get("end"),
                    "timeline_in": round(cursor, 3),
                    "timeline_out": round(cursor + duration, 3),
                    "speed": item.get("speed", 1.0),
                    "slow_motion": item.get("slow_motion") or {},
                    "fit": "smart_center_9x16",
                    "crop_center": item.get("crop_center") or [0.5, 0.5],
                    "role": item.get("role", "beat_cut"),
                    "camera_instruction": item.get("camera_instruction") or {},
                },
            }
        )
        if item.get("transition") and item.get("transition") != "hard_cut":
            actions.append(
                {
                    "action": "add_transition",
                    "params": {
                        "at": round(cursor, 3),
                        "type": item.get("transition"),
                        "duration": _transition_duration(str(item.get("transition"))),
                        "instruction": item.get("transition_instruction") or {},
                    },
                }
            )
        if item.get("effect") and item.get("effect") != "none":
            actions.append(
                {
                    "action": "add_effect",
                    "params": {
                        "target": f"clip_{index + 1:03d}",
                        "type": item.get("effect"),
                        "strength": 0.6,
                        "instruction": item.get("camera_instruction") or {},
                        "slow_motion": item.get("slow_motion") or {},
                    },
                }
            )
        cursor += duration

    if state.bgm:
        actions.append(
            {
                "action": "add_audio",
                "params": {
                    "track": "bgm",
                    "media_id": state.bgm,
                    "timeline_in": 0,
                    "timeline_out": round(float(timeline.get("target_duration", cursor)), 3),
                    "volume": 0.95,
                },
            }
        )

    actions.append({"action": "apply_color_grade", "params": {"preset": timeline.get("color_grade", "cool_white_soft")}})
    actions.append(
        {
            "action": "export_video",
            "params": {
                "path": str(project_asset_dir("outputs", state.project_id) / "output.mp4"),
                "codec": "h264",
                "quality": "high",
            },
        }
    )
    return {
        "schema": "ai-fancut.capcut-actions.v1",
        "project_id": state.project_id,
        "timeline_title": timeline.get("title", "AI Fancut"),
        "target_duration": timeline.get("target_duration"),
        "execution_ready": not warnings,
        "warnings": warnings,
        "actions": actions,
    }


def _transition_duration(transition: str) -> float:
    return {
        "flash_white": 0.14,
        "flash_black": 0.16,
        "glow_flash": 0.2,
        "strobe_white": 0.12,
        "whip_flash": 0.16,
        "crossfade": 0.22,
        "soft_wash": 0.26,
        "bloom_blur": 0.24,
        "whip_pan": 0.2,
        "luma_fade": 0.22,
        "zoom_burst": 0.24,
        "spin_blur": 0.28,
        "rotate_flash": 0.22,
        "shake_zoom": 0.22,
    }.get(transition, 0.18)
