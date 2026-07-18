from typing import Any

from app.models.schemas import ProjectState


def project_target_duration(
    state: ProjectState,
    requested: int | None = None,
    style: dict[str, Any] | None = None,
    fallback: int = 30,
) -> int:
    beats = state.beats or {}
    if beats.get("target_duration"):
        return max(1, int(round(float(beats["target_duration"]))))
    if requested:
        return max(1, int(requested))
    if style and style.get("recommended_duration"):
        return max(1, int(round(float(style["recommended_duration"]))))
    return fallback


def timeline_target_duration(timeline: dict[str, Any], fallback: float | None = None) -> float | None:
    duration = timeline.get("target_duration") or fallback
    if duration is None:
        return None
    try:
        return max(0.1, float(duration))
    except (TypeError, ValueError):
        return None
