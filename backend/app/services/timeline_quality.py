from collections import Counter
from typing import Any


def build_timeline_quality_report(timeline: dict[str, Any], source_names: list[str]) -> dict[str, Any]:
    items = timeline.get("timeline", []) or []
    sources = [str(item.get("source", "")) for item in items if item.get("source")]
    usage = Counter(sources)
    source_families = [_source_family(source) for source in sources]
    family_usage = Counter(source_families)
    available_families = {_source_family(str(name)) for name in source_names if name}
    total_items = len(items)
    unique_sources = len(usage)
    available_sources = len(source_names)
    unique_families = len(family_usage)
    available_family_count = len(available_families)
    total_duration = round(sum(max(0.0, float(item.get("end", 0)) - float(item.get("start", 0))) for item in items), 2)
    consecutive_repeats = _consecutive_repeat_count(sources)
    crop_coverage = _crop_coverage(items)
    effects = [str(item.get("effect", "")) for item in items if item.get("effect")]
    transitions = [str(item.get("transition", "")) for item in items if item.get("transition")]
    effect_repeats = _consecutive_repeat_count(effects)
    transition_repeats = _consecutive_repeat_count(transitions)
    top_source_share = max(usage.values(), default=0) / max(1, total_items)
    music_picture = _music_picture_report(items)
    slow_motion = _slow_motion_report(items)
    top_source_family_share = max(family_usage.values(), default=0) / max(1, total_items)

    warnings: list[str] = []
    if available_sources > 1 and unique_sources < available_sources:
        warnings.append("Some uploaded sources are not represented in the timeline.")
    if available_family_count > 1 and unique_families < available_family_count:
        warnings.append("One original video family is missing; the edit may look like it only used one upload.")
    if available_family_count > 1 and top_source_family_share > 0.68:
        warnings.append("One original video family dominates the edit; add contrast or source-family alternation.")
    if total_items > 0 and consecutive_repeats / total_items > 0.22:
        warnings.append("Consecutive source reuse is high; the edit may feel repetitive.")
    if total_items > 0 and top_source_share > 0.42:
        warnings.append("One source dominates the edit; add source cooldown or more alternation.")
    if effects and effect_repeats / max(1, len(effects)) > 0.2:
        warnings.append("Consecutive effect reuse is high; motion may feel mechanical.")
    if transitions and transition_repeats / max(1, len(transitions)) > 0.28:
        warnings.append("Consecutive transition reuse is high; reduce repeated flashes/cuts.")
    if crop_coverage < 0.7:
        warnings.append("Some clips lack crop-center information for subject-safe vertical framing.")
    if music_picture["strong_beat_hit_rate"] < 0.55:
        warnings.append("Strong beats do not have enough visual change.")
    if music_picture["drop_visual_change_avg"] < 0.55 and music_picture["drop_item_count"] > 0:
        warnings.append("Drop section lacks a clear visual lift.")
    if music_picture["weak_section_overcut_count"] > 1:
        warnings.append("Intro/outro uses too many heavy cuts or effects.")
    warnings.extend(slow_motion["warnings"])

    return {
        "total_items": total_items,
        "unique_sources": unique_sources,
        "available_sources": available_sources,
        "source_usage": dict(usage),
        "source_family_usage": dict(family_usage),
        "available_source_families": available_family_count,
        "consecutive_repeat_count": consecutive_repeats,
        "effect_repeat_count": effect_repeats,
        "transition_repeat_count": transition_repeats,
        "top_source_share": round(top_source_share, 3),
        "top_source_family_share": round(top_source_family_share, 3),
        "timeline_source_diversity": round(unique_sources / max(1, available_sources), 3),
        "timeline_source_family_diversity": round(unique_families / max(1, available_family_count), 3),
        "crop_center_coverage": crop_coverage,
        "music_picture_score": music_picture["score"],
        "music_picture": music_picture,
        "slow_motion": slow_motion,
        "raw_clip_duration_sum": total_duration,
        "warnings": warnings,
    }


def _source_family(source: str) -> str:
    if "_" in source:
        return source.split("_", 1)[1]
    return source


def _consecutive_repeat_count(values: list[str]) -> int:
    return sum(1 for prev, current in zip(values, values[1:]) if prev == current)


def _crop_coverage(items: list[dict[str, Any]]) -> float:
    if not items:
        return 0.0
    with_crop = sum(1 for item in items if item.get("crop_center"))
    return round(with_crop / len(items), 3)


def _music_picture_report(items: list[dict[str, Any]]) -> dict[str, Any]:
    if not items:
        return {
            "score": 0.0,
            "strong_beat_hit_rate": 0.0,
            "drop_visual_change_avg": 0.0,
            "drop_item_count": 0,
            "weak_section_overcut_count": 0,
            "same_section_effect_repeat_count": 0,
            "section_balance": {},
        }
    strong_items = [item for item in items if item.get("beat_hit")]
    strong_hits = [
        item
        for item in strong_items
        if float(item.get("visual_change_strength", 0) or 0) >= 0.55
        or item.get("transition") not in {"", "hard_cut", None}
    ]
    drop_items = [item for item in items if item.get("music_section") == "drop"]
    weak_items = [item for item in items if item.get("music_section") in {"intro", "outro"}]
    weak_overcuts = [
        item
        for item in weak_items
        if float(item.get("visual_change_strength", 0) or 0) >= 0.72
        or item.get("transition") in {"flash_white", "whip_flash", "strobe_white", "whip_pan", "bloom_blur", "zoom_burst", "spin_blur", "rotate_flash", "shake_zoom"}
    ]
    section_counts = Counter(str(item.get("music_section", "unknown")) for item in items)
    same_section_effect_repeats = _same_section_effect_repeat(items)
    strong_rate = len(strong_hits) / max(1, len(strong_items))
    drop_avg = sum(float(item.get("visual_change_strength", 0) or 0) for item in drop_items) / max(1, len(drop_items))
    score = 82.0
    score += strong_rate * 18
    score += drop_avg * 16
    score -= len(weak_overcuts) * 5
    score -= same_section_effect_repeats * 3
    return {
        "score": round(max(0.0, min(120.0, score)), 2),
        "strong_beat_item_count": len(strong_items),
        "strong_beat_hit_rate": round(strong_rate, 3),
        "drop_visual_change_avg": round(drop_avg, 3),
        "drop_item_count": len(drop_items),
        "weak_section_overcut_count": len(weak_overcuts),
        "same_section_effect_repeat_count": same_section_effect_repeats,
        "section_balance": dict(section_counts),
    }


def _same_section_effect_repeat(items: list[dict[str, Any]]) -> int:
    count = 0
    for prev, current in zip(items, items[1:]):
        if prev.get("music_section") == current.get("music_section") and prev.get("effect") == current.get("effect"):
            count += 1
    return count


def _slow_motion_report(items: list[dict[str, Any]]) -> dict[str, Any]:
    slow_items = []
    warnings: list[str] = []
    consecutive = 0
    max_consecutive = 0
    violations = []
    for index, item in enumerate(items):
        speed = float(item.get("speed", 1.0) or 1.0)
        enabled = bool((item.get("slow_motion") or {}).get("enabled")) or speed < 0.8
        if enabled:
            consecutive += 1
            max_consecutive = max(max_consecutive, consecutive)
            slow_items.append(index)
            if speed < 0.2 or 0.8 <= speed < 1.0:
                violations.append({"index": index, "reason": "invalid_speed", "speed": speed})
            if item.get("role") in {"opening_hook", "setup", "pre_transform"} or item.get("music_section") == "intro":
                violations.append({"index": index, "reason": "forbidden_opening_or_setup"})
            if item.get("shot_size") not in {"closeup", "medium_closeup", "half_body"}:
                violations.append({"index": index, "reason": "not_face_or_upper_body"})
            if not (item.get("beat_hit") or item.get("role") in {"transform_hit", "climax", "ending"} or item.get("music_section") in {"drop", "outro"}):
                violations.append({"index": index, "reason": "missing_turning_point"})
        else:
            consecutive = 0
    if max_consecutive > 2:
        warnings.append("Slow motion appears in more than 2 consecutive clips; insert normal-speed separation.")
    if violations:
        warnings.append("Slow motion policy violations detected; review trigger timing, subject size, and speed ranges.")
    return {
        "slow_clip_count": len(slow_items),
        "slow_clip_indexes": slow_items,
        "max_consecutive_slow_clips": max_consecutive,
        "violations": violations[:12],
        "warnings": warnings,
    }
