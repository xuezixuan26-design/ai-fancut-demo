from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any

from app.models.schemas import ProjectState
from app.services.timeline_quality import build_timeline_quality_report
from app.utils.file_utils import project_dir
from app.utils.json_utils import write_json


def critique_project_edit(state: ProjectState) -> dict[str, Any]:
    timeline = deepcopy(state.timeline or {})
    quality = timeline.get("quality_report") or build_timeline_quality_report(timeline, state.videos)
    items = timeline.get("timeline", []) or []
    reference_understanding = _reference_understanding(state.reference_style or {})
    annotations = _timeline_annotations(items, quality, reference_understanding)
    report = {
        "schema": "ai-fancut.edit-critic.v1",
        "project_id": state.project_id,
        "critic_goal": "watch_reference_and_current_edit_then_propose_timeline_revision",
        "reference_understanding": reference_understanding,
        "quality_snapshot": quality,
        "annotations": annotations,
        "summary": _critic_summary(annotations, quality),
        "proposed_actions": _proposed_actions(annotations, quality),
    }
    write_json(project_dir(state.project_id) / "edit_critic_report.json", report)
    return report


def revise_timeline_from_critic(state: ProjectState, critic_report: dict[str, Any] | None = None) -> dict[str, Any]:
    if not state.timeline:
        raise ValueError("Timeline not generated")
    report = critic_report or critique_project_edit(state)
    timeline = deepcopy(state.timeline)
    items = [dict(item) for item in timeline.get("timeline", []) or []]
    actions = report.get("proposed_actions") or []
    changes: list[dict[str, Any]] = []

    for action in actions:
        kind = action.get("type")
        if kind == "reduce_source_dominance":
            changes.extend(_reduce_source_dominance(items, state.candidate_clips))
        elif kind == "increase_drop_lift":
            changes.extend(_increase_drop_lift(items))
        elif kind == "soften_intro_outro":
            changes.extend(_soften_intro_outro(items))
        elif kind == "vary_repeated_effects":
            changes.extend(_vary_repeated_effects(items))
        elif kind == "repair_slow_motion":
            changes.extend(_repair_slow_motion(items))
        elif kind == "add_turning_point_slow_motion":
            changes.extend(_add_turning_point_slow_motion(items))

    _recompute_output_times(items)
    timeline["timeline"] = items
    timeline["quality_report"] = build_timeline_quality_report(timeline, state.videos)
    timeline["critic_revision"] = {
        "schema": "ai-fancut.timeline-revision.v1",
        "source": "edit_critic",
        "revision_index": int((state.timeline.get("critic_revision") or {}).get("revision_index", 0)) + 1,
        "applied_action_count": len(actions),
        "change_count": len(changes),
        "changes": changes[:80],
        "critic_summary": report.get("summary", {}),
    }
    write_json(project_dir(state.project_id) / f"timeline_v{timeline['critic_revision']['revision_index'] + 1}.json", timeline)
    write_json(project_dir(state.project_id) / "critic_revised_timeline.json", timeline)
    return {
        "schema": "ai-fancut.critic-revision-result.v1",
        "project_id": state.project_id,
        "revision_index": timeline["critic_revision"]["revision_index"],
        "change_count": len(changes),
        "quality_report": timeline["quality_report"],
        "timeline": timeline,
    }


def _reference_understanding(style: dict[str, Any]) -> dict[str, Any]:
    existing = style.get("reference_understanding") or {}
    rhythm = existing.get("rhythm_curve") or _fallback_rhythm_curve(style)
    return {
        "schema": "ai-fancut.reference-understanding.v1",
        "edit_profile": style.get("edit_profile"),
        "structure": existing.get("structure") or rhythm,
        "rhythm_curve": rhythm,
        "shot_relation_rules": existing.get("shot_relation_rules")
        or [
            "opening establishes subject and atmosphere before heavy effects",
            "build section increases cut density or camera energy gradually",
            "turning point should be followed by a visual lift or slow-motion hold",
            "drop/climax must alternate action impact with face/upper-body memory points",
            "ending should reduce motion and leave one clear final memory frame",
        ],
        "turning_point_hints": existing.get("turning_point_hints")
        or {
            "opening_to_build": 0.18,
            "build_to_drop": 0.48,
            "drop_to_outro": 0.82,
            "slow_motion_after_turn": True,
        },
        "planner_hints": existing.get("planner_hints")
        or {
            "prefer_revision_loop": True,
            "critic_should_check": ["source_repeat", "music_picture", "slow_motion", "transition_variety", "drop_lift"],
        },
    }


def _fallback_rhythm_curve(style: dict[str, Any]) -> list[dict[str, Any]]:
    profile = style.get("edit_profile", "")
    if profile == "monochrome_to_color_beauty":
        return [
            {"section": "atmosphere", "range": [0.0, 0.18], "energy": 0.25, "goal": "mystery setup"},
            {"section": "reveal", "range": [0.18, 0.4], "energy": 0.45, "goal": "clarity and color rise"},
            {"section": "beauty_hold", "range": [0.4, 0.82], "energy": 0.58, "goal": "face memory"},
            {"section": "ending", "range": [0.82, 1.0], "energy": 0.35, "goal": "final hold"},
        ]
    return [
        {"section": "opening", "range": [0.0, 0.18], "energy": 0.35, "goal": "subject setup"},
        {"section": "build", "range": [0.18, 0.48], "energy": 0.55, "goal": "rhythm build"},
        {"section": "drop", "range": [0.48, 0.82], "energy": 0.82, "goal": "visual lift"},
        {"section": "outro", "range": [0.82, 1.0], "energy": 0.5, "goal": "memory point"},
    ]


def _timeline_annotations(items: list[dict[str, Any]], quality: dict[str, Any], reference: dict[str, Any]) -> list[dict[str, Any]]:
    annotations: list[dict[str, Any]] = []
    source_counts = Counter(str(item.get("source")) for item in items if item.get("source"))
    dominant_source, dominant_count = source_counts.most_common(1)[0] if source_counts else ("", 0)
    top_share = quality.get("top_source_share", 0) or 0
    if top_share > 0.42:
        annotations.append(_annotation("source_repeat", 0, "One source dominates the edit.", "medium", {"source": dominant_source, "count": dominant_count, "share": top_share}))
    music = quality.get("music_picture") or {}
    if music.get("drop_visual_change_avg", 1) < 0.6 and music.get("drop_item_count", 0) > 0:
        annotations.append(_annotation("drop_lift_weak", _first_section_time(items, "drop"), "Drop section lacks enough visual lift after the rhythm turn.", "high", music))
    if music.get("weak_section_overcut_count", 0) > 1:
        annotations.append(_annotation("intro_outro_overcut", 0, "Intro/outro uses too many heavy effects for setup or memory hold.", "medium", music))
    slow = quality.get("slow_motion") or {}
    if slow.get("violations"):
        annotations.append(_annotation("slow_motion_violation", 0, "Slow motion violates timing, subject, or consecutive-count rules.", "high", slow))
    elif not slow.get("slow_clip_count") and items:
        annotations.append(_annotation("missing_turn_slow_motion", _first_section_time(items, "drop"), "No slow-motion hold after the main rhythm turn.", "medium", {"reference_turning_points": reference.get("turning_point_hints")}))
    if quality.get("effect_repeat_count", 0) > 0 or quality.get("transition_repeat_count", 0) > 0:
        annotations.append(
            _annotation(
                "mechanical_repetition",
                0,
                "Repeated effects or transitions make the edit feel template-driven.",
                "medium",
                {"effect_repeat_count": quality.get("effect_repeat_count"), "transition_repeat_count": quality.get("transition_repeat_count")},
            )
        )
    for warning in quality.get("warnings", [])[:6]:
        annotations.append(_annotation("quality_warning", 0, str(warning), "low", {}))
    return annotations


def _annotation(kind: str, time_sec: float, message: str, severity: str, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": kind,
        "time_sec": round(float(time_sec or 0), 3),
        "severity": severity,
        "message": message,
        "evidence": evidence,
    }


def _critic_summary(annotations: list[dict[str, Any]], quality: dict[str, Any]) -> dict[str, Any]:
    high = sum(1 for item in annotations if item.get("severity") == "high")
    medium = sum(1 for item in annotations if item.get("severity") == "medium")
    return {
        "issue_count": len(annotations),
        "high_count": high,
        "medium_count": medium,
        "ready_for_final": high == 0 and medium <= 1,
        "music_picture_score": quality.get("music_picture_score"),
    }


def _proposed_actions(annotations: list[dict[str, Any]], quality: dict[str, Any]) -> list[dict[str, Any]]:
    kinds = {item.get("kind") for item in annotations}
    actions = []
    if "source_repeat" in kinds:
        actions.append({"type": "reduce_source_dominance", "reason": "source_repeat"})
    if "drop_lift_weak" in kinds:
        actions.append({"type": "increase_drop_lift", "reason": "drop_lift_weak"})
    if "intro_outro_overcut" in kinds:
        actions.append({"type": "soften_intro_outro", "reason": "intro_outro_overcut"})
    if "mechanical_repetition" in kinds:
        actions.append({"type": "vary_repeated_effects", "reason": "mechanical_repetition"})
    if "slow_motion_violation" in kinds:
        actions.append({"type": "repair_slow_motion", "reason": "slow_motion_violation"})
    if "missing_turn_slow_motion" in kinds:
        actions.append({"type": "add_turning_point_slow_motion", "reason": "missing_turn_slow_motion"})
    if quality.get("music_picture_score", 100) < 92:
        actions.append({"type": "increase_drop_lift", "reason": "music_picture_score"})
    return _dedupe_actions(actions)


def _dedupe_actions(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    result = []
    for action in actions:
        key = action.get("type")
        if key in seen:
            continue
        seen.add(key)
        result.append(action)
    return result


def _first_section_time(items: list[dict[str, Any]], section: str) -> float:
    for item in items:
        if item.get("music_section") == section:
            return float(item.get("output_start") or 0)
    return 0.0


def _reduce_source_dominance(items: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    changes = []
    if not items or not candidates:
        return changes
    sources = [str(item.get("source")) for item in items if item.get("source")]
    counts = Counter(sources)
    if not counts:
        return changes
    dominant = counts.most_common(1)[0][0]
    alternatives = [clip for clip in candidates if str(clip.get("source")) != dominant]
    if not alternatives:
        return changes
    alt_index = 0
    for index, item in enumerate(items):
        if index % 3 != 2 or str(item.get("source")) != dominant:
            continue
        replacement = _best_replacement(item, alternatives, alt_index)
        alt_index += 1
        original_duration = max(0.35, float(item.get("end", 0) or 0) - float(item.get("start", 0) or 0))
        item["source"] = replacement["source"]
        item["start"] = replacement["start"]
        item["end"] = round(float(replacement["start"]) + min(original_duration, max(0.4, float(replacement["end"]) - float(replacement["start"]))), 3)
        item["shot_size"] = replacement.get("shot_size", item.get("shot_size"))
        item["subject_position"] = replacement.get("subject_position", item.get("subject_position"))
        item["crop_center"] = replacement.get("crop_center", item.get("crop_center"))
        changes.append({"type": "replace_clip_source", "index": index, "source": item["source"]})
    return changes


def _best_replacement(item: dict[str, Any], alternatives: list[dict[str, Any]], offset: int) -> dict[str, Any]:
    shot = item.get("shot_size")
    preferred = [clip for clip in alternatives if clip.get("shot_size") == shot] or alternatives
    return sorted(preferred, key=lambda clip: float(clip.get("highlight_score", 0) or 0), reverse=True)[offset % len(preferred)]


def _increase_drop_lift(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    changes = []
    transitions = ["zoom_burst", "rotate_flash", "bloom_blur", "shake_zoom"]
    effects = ["zoom_punch", "snap_zoom", "slowmo_beat_freeze", "whip_push"]
    for index, item in enumerate(items):
        if item.get("music_section") != "drop":
            continue
        if item.get("beat_hit") or index % 2 == 0:
            item["transition"] = transitions[index % len(transitions)] if index else item.get("transition", "hard_cut")
            item["effect"] = effects[index % len(effects)]
            changes.append({"type": "increase_drop_lift", "index": index, "effect": item["effect"], "transition": item.get("transition")})
    return changes


def _soften_intro_outro(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    changes = []
    heavy_transitions = {"flash_white", "whip_flash", "strobe_white", "whip_pan", "bloom_blur", "zoom_burst", "spin_blur", "rotate_flash", "shake_zoom"}
    heavy_effects = {"zoom_punch", "snap_zoom", "beat_shake", "whip_push"}
    for index, item in enumerate(items):
        if item.get("music_section") not in {"intro", "outro"}:
            continue
        changed = False
        if item.get("transition") in heavy_transitions:
            item["transition"] = "soft_wash" if item.get("music_section") == "intro" else "crossfade"
            changed = True
        if item.get("effect") in heavy_effects:
            item["effect"] = "slow_motion_glow" if item.get("music_section") == "outro" else "slow_zoom_in"
            changed = True
        if changed:
            changes.append({"type": "soften_intro_outro", "index": index})
    return changes


def _vary_repeated_effects(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    changes = []
    alternates = ["slow_zoom_in", "drift_zoom", "soft_glow", "zoom_punch", "breathing_zoom", "hair_rim_light"]
    transition_alternates = ["hard_cut", "soft_wash", "glow_flash", "zoom_burst", "bloom_blur", "crossfade"]
    for index in range(1, len(items)):
        if items[index].get("effect") == items[index - 1].get("effect"):
            items[index]["effect"] = alternates[index % len(alternates)]
            changes.append({"type": "vary_effect", "index": index, "effect": items[index]["effect"]})
        if items[index].get("transition") == items[index - 1].get("transition") and items[index].get("transition") != "hard_cut":
            items[index]["transition"] = transition_alternates[index % len(transition_alternates)]
            changes.append({"type": "vary_transition", "index": index, "transition": items[index]["transition"]})
    return changes


def _repair_slow_motion(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    changes = []
    consecutive = 0
    for index, item in enumerate(items):
        is_slow = bool((item.get("slow_motion") or {}).get("enabled")) or float(item.get("speed", 1.0) or 1.0) < 0.8
        allowed = item.get("music_section") not in {"intro"} and item.get("shot_size") in {"closeup", "medium_closeup", "half_body"} and consecutive < 2
        if is_slow and not allowed:
            item["speed"] = 1.0
            item["slow_motion"] = {"enabled": False, "trigger": "critic_repaired"}
            changes.append({"type": "repair_slow_motion", "index": index})
            consecutive = 0
        elif is_slow:
            consecutive += 1
        else:
            consecutive = 0
    return changes


def _add_turning_point_slow_motion(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for index, item in enumerate(items):
        if item.get("music_section") != "drop":
            continue
        if item.get("shot_size") not in {"closeup", "medium_closeup", "half_body"}:
            continue
        item["speed"] = 0.6
        item["effect"] = "slow_motion_glow"
        item["slow_motion"] = {
            "enabled": True,
            "trigger": "critic_added_after_turning_point",
            "speed_range": "0.5-0.7",
            "render_priority": ["face_highlight", "hair_rim_light", "soft_glow"],
        }
        return [{"type": "add_turning_point_slow_motion", "index": index}]
    return []


def _recompute_output_times(items: list[dict[str, Any]]) -> None:
    cursor = 0.0
    for item in items:
        try:
            raw = max(0.1, float(item.get("end", 0)) - float(item.get("start", 0)))
            speed = max(0.2, float(item.get("speed", 1.0) or 1.0))
        except (TypeError, ValueError):
            raw, speed = 0.8, 1.0
        duration = raw / speed
        item["output_start"] = round(cursor, 3)
        item["output_end"] = round(cursor + duration, 3)
        cursor += duration
