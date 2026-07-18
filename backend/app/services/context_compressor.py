from collections import Counter
from typing import Any

from app.models.schemas import ProjectState
from app.services.knowledge_base import upsert_project_memory
from app.utils.file_utils import project_dir
from app.utils.json_utils import write_json


def compress_project_context(state: ProjectState, feedback: str | None = None) -> dict[str, Any]:
    timeline = state.timeline or {}
    items = timeline.get("timeline", []) or []
    quality = timeline.get("quality_report", {}) or {}
    reference_style = state.reference_style or {}

    summary = {
        "schema": "ai-fancut.context-summary.v1",
        "project_id": state.project_id,
        "style_fingerprint": _style_fingerprint(reference_style, timeline),
        "edit_summary": _edit_summary(items, quality),
        "asset_summary": _asset_summary(state),
        "preference_delta": _preference_delta(feedback),
        "reuse_hints": _reuse_hints(reference_style, items, quality, feedback),
    }
    write_json(project_dir(state.project_id) / "context_summary.json", summary)
    upsert_project_memory(summary)
    return summary


def _style_fingerprint(reference_style: dict[str, Any], timeline: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "template",
        "edit_profile",
        "opening_pattern",
        "climax_pattern",
        "motion_profile",
        "effect_intensity",
        "caption_frequency",
        "cut_density",
        "color_grade",
        "layout_profile",
        "aspect_ratio",
    ]
    fingerprint = {key: reference_style.get(key) for key in keys if reference_style.get(key) is not None}
    fingerprint.update(timeline.get("style_fingerprint") or {})
    if timeline.get("aspect_ratio"):
        fingerprint["aspect_ratio"] = timeline.get("aspect_ratio")
    return fingerprint


def _edit_summary(items: list[dict[str, Any]], quality: dict[str, Any]) -> dict[str, Any]:
    effects = Counter(str(item.get("effect", "none")) for item in items)
    transitions = Counter(str(item.get("transition", "hard_cut")) for item in items)
    roles = Counter(str(item.get("role", "beat_cut")) for item in items)
    sources = Counter(str(item.get("source", "")) for item in items if item.get("source"))
    duration = round(
        sum(
            max(0.1, float(item.get("end", 0)) - float(item.get("start", 0)))
            / max(0.2, float(item.get("speed", 1.0) or 1.0))
            for item in items
        ),
        2,
    )
    return {
        "duration": duration,
        "total_items": len(items),
        "top_roles": roles.most_common(6),
        "top_effects": effects.most_common(8),
        "top_transitions": transitions.most_common(8),
        "source_usage": dict(sources),
        "quality": {
            "timeline_source_diversity": quality.get("timeline_source_diversity"),
            "crop_center_coverage": quality.get("crop_center_coverage"),
            "consecutive_repeat_count": quality.get("consecutive_repeat_count"),
            "effect_repeat_count": quality.get("effect_repeat_count"),
            "transition_repeat_count": quality.get("transition_repeat_count"),
            "top_source_share": quality.get("top_source_share"),
            "warnings": quality.get("warnings", []),
        },
    }


def _asset_summary(state: ProjectState) -> dict[str, Any]:
    return {
        "videos": len(state.videos),
        "has_bgm": bool(state.bgm),
        "has_reference": bool(state.reference),
        "candidate_clips": len(state.candidate_clips),
        "frame_analysis_rows": len(state.frame_analysis),
    }


def _preference_delta(feedback: str | None) -> dict[str, Any]:
    if not feedback:
        return {"raw_feedback": "", "signals": []}
    rules = {
        "less_repetition": ["重复", "反复", "机械"],
        "stronger_music_structure": ["音乐", "节奏", "卡点", "鼓点"],
        "more_face_focus": ["脸", "颜值", "五官", "皮肤"],
        "subtler_effects": ["花哨", "复杂", "过度", "抢"],
        "better_reference_match": ["参考", "复刻", "不像", "差异"],
    }
    signals = [name for name, words in rules.items() if any(word in feedback for word in words)]
    return {"raw_feedback": feedback, "signals": signals}


def _reuse_hints(
    reference_style: dict[str, Any],
    items: list[dict[str, Any]],
    quality: dict[str, Any],
    feedback: str | None,
) -> list[str]:
    hints: list[str] = []
    edit_profile = reference_style.get("edit_profile")
    if edit_profile:
        hints.append(f"prefer_edit_profile:{edit_profile}")
    if quality.get("top_source_share", 0) and float(quality.get("top_source_share", 0)) > 0.42:
        hints.append("increase_source_cooldown")
    if quality.get("effect_repeat_count", 0):
        hints.append("avoid_consecutive_effects")
    if any(item.get("role") == "opening_hook" for item in items):
        hints.append("preserve_opening_hook_role")
    if feedback:
        hints.extend(_preference_delta(feedback)["signals"])
    return sorted(set(hints))
