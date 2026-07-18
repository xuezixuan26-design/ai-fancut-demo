from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import shutil
from typing import Any

from app.models.schemas import ProjectState
from app.utils.file_utils import project_asset_dir, project_dir
from app.utils.json_utils import read_json, write_json


INDEX_FILE = "render_history.json"


def archive_render_output(state: ProjectState, output_path: Path) -> dict[str, Any]:
    if not output_path.exists():
        raise FileNotFoundError(f"Render output not found: {output_path}")

    entries = load_render_history(state.project_id)
    version = _next_version(entries)
    history_dir = project_asset_dir("outputs", state.project_id) / "render_history"
    history_dir.mkdir(parents=True, exist_ok=True)
    project_history_dir = project_dir(state.project_id) / "render_history"
    project_history_dir.mkdir(parents=True, exist_ok=True)

    output_name = f"output_v{version:03d}.mp4"
    timeline_name = f"timeline_v{version:03d}.json"
    metadata_name = f"metadata_v{version:03d}.json"
    archived_video = history_dir / output_name
    archived_timeline = project_history_dir / timeline_name
    archived_metadata = project_history_dir / metadata_name

    shutil.copy2(output_path, archived_video)
    write_json(archived_timeline, state.timeline or {})

    quality = (state.timeline or {}).get("quality_report") or {}
    promoted = (state.timeline or {}).get("promoted_from_harness") or {}
    metadata = {
        "schema": "ai-fancut.render-history-entry.v1",
        "project_id": state.project_id,
        "version": version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "video_file": output_name,
        "video_url": f"/api/render/history/{state.project_id}/{version}",
        "timeline_file": str(archived_timeline.name),
        "metadata_file": str(archived_metadata.name),
        "style_template": promoted.get("style_template") or (state.timeline or {}).get("template_profile_id") or (state.timeline or {}).get("style"),
        "score": promoted.get("score"),
        "target_duration": (state.timeline or {}).get("target_duration"),
        "aspect_ratio": (state.timeline or {}).get("aspect_ratio") or state.aspect_ratio,
        "timeline_items": len((state.timeline or {}).get("timeline", []) or []),
        "source_usage": quality.get("source_usage", {}),
        "source_family_usage": quality.get("source_family_usage", {}),
        "music_picture_score": quality.get("music_picture_score"),
        "warnings": quality.get("warnings", []),
        "file_size": archived_video.stat().st_size,
    }
    write_json(archived_metadata, metadata)

    entries.append(metadata)
    write_json(_index_path(state.project_id), entries)
    state.render_history = entries
    return metadata


def load_render_history(project_id: str) -> list[dict[str, Any]]:
    entries = read_json(_index_path(project_id), default=[])
    if not isinstance(entries, list):
        return []
    return entries


def render_history_video_path(project_id: str, version: int) -> Path:
    entry = next((item for item in load_render_history(project_id) if int(item.get("version", -1)) == int(version)), None)
    if not entry:
        raise FileNotFoundError(f"Render history version not found: {project_id} v{version}")
    return project_asset_dir("outputs", project_id) / "render_history" / str(entry["video_file"])


def _index_path(project_id: str) -> Path:
    return project_dir(project_id) / INDEX_FILE


def _next_version(entries: list[dict[str, Any]]) -> int:
    versions = []
    for entry in entries:
        try:
            versions.append(int(entry.get("version", 0)))
        except (TypeError, ValueError):
            continue
    return max(versions, default=0) + 1
