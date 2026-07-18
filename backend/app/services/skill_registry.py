from functools import lru_cache
import json
from pathlib import Path
from typing import Any


SKILL_PATH = Path(__file__).resolve().parents[1] / "skills" / "skill_registry.json"


@lru_cache(maxsize=1)
def load_skills() -> list[dict[str, Any]]:
    with SKILL_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def skill_summary(skill: dict[str, Any], confidence: float, reason: str) -> dict[str, Any]:
    return {
        "skill_id": skill["skill_id"],
        "skill_name": skill["skill_name"],
        "type": skill.get("type", "technical"),
        "confidence": round(confidence, 2),
        "reason": reason,
    }


def select_skills(reference_style: dict, candidate_clips: list[dict], beats: dict) -> list[dict[str, Any]]:
    skills = {skill["skill_id"]: skill for skill in load_skills()}
    if not candidate_clips:
        return [skill_summary(skills["weak_material_rescue"], 0.9, "没有可用候选片段，进入弱素材救片策略")]

    best_score = max(float(clip.get("highlight_score", 0)) for clip in candidate_clips)
    avg_face_ratio = sum(float(clip.get("face_ratio", 0)) for clip in candidate_clips) / len(candidate_clips)
    stage_like = _has_stage_like_clip(candidate_clips) or reference_style.get("edit_profile") == "stage_beat_cut"
    beat_count = len(beats.get("beats", []))
    has_closeup = any(clip.get("shot_size") in {"closeup", "medium_closeup"} for clip in candidate_clips)
    has_transform_cue = _has_transform_cue(reference_style, candidate_clips)
    high_cut_reference = reference_style.get("cut_density") == "high"
    progressive_beauty = reference_style.get("edit_profile") == "progressive_idol_beauty"
    monochrome_beauty = reference_style.get("edit_profile") == "monochrome_to_color_beauty"
    contrast_two_video = reference_style.get("edit_profile") == "contrast_two_video" or reference_style.get("template") == "contrast_special"

    selected: list[dict[str, Any]] = []
    if progressive_beauty and "progressive_idol_beauty_arc" in skills:
        selected.append(skill_summary(skills["progressive_idol_beauty_arc"], 0.86, "参考风格需要先建立人物、再动作递进、再进入核心展示和高潮收尾"))
    if monochrome_beauty and "monochrome_to_color_beauty_reveal" in skills:
        selected.append(skill_summary(skills["monochrome_to_color_beauty_reveal"], 0.88, "参考风格需要黑白/低饱和氛围到高清彩色颜值展示的微递进"))
    if contrast_two_video and "contrast_special_two_video" in skills:
        selected.append(skill_summary(skills["contrast_special_two_video"], 0.9, "contrast template requires two source-family setup/reveal planning"))
    if best_score >= 7.0 or avg_face_ratio >= 0.08 or has_closeup:
        selected.append(skill_summary(skills["beauty_hook_opening"], 0.84, "存在高分近景/特写片段，适合开头抓人"))
        selected.append(skill_summary(skills["cool_white_beauty_closeup"], 0.78, "候选素材里有人脸清晰的颜值展示片段"))
    if stage_like:
        selected.append(skill_summary(skills["red_black_stage_tracking"], 0.74, "素材或参考风格有舞台光感/运动感倾向"))
        selected.append(skill_summary(skills["multi_layer_stage_climax"], 0.7, "可组织为舞台高潮多轨结构"))
    if beat_count >= 8:
        selected.append(skill_summary(skills["stage_beat_zoom_cut"], 0.82, "BGM 节拍数量足够，适合卡点快切"))
        selected.append(skill_summary(skills["beat_keyframe_flash_focus"], 0.72, "强拍可用于关键帧推拉和闪白聚焦"))
    if high_cut_reference or reference_style.get("dark_reveal_times"):
        selected.append(skill_summary(skills["black_fog_opening_reveal"], 0.64, "参考风格存在高密度切换或暗场 reveal 倾向"))
    if has_transform_cue:
        selected.append(skill_summary(skills["transform_reveal_adaptive"], 0.68, "检测到可承接变装/反差 reveal 的节奏或闪白线索"))
    selected.append(skill_summary(skills["ending_freeze_memory"], 0.74, "需要稳定收束和结尾记忆点"))

    if len(candidate_clips) < 4 or best_score < 5.5:
        selected.append(skill_summary(skills["weak_material_rescue"], 0.84, "候选片段数量或质量不足，准备降级生成"))

    return _dedupe(selected)


def build_tracks(
    timeline: list[dict[str, Any]],
    applied_skills: list[dict[str, Any]],
    beats: dict,
    target_duration: float,
) -> list[dict[str, Any]]:
    main_items = [
        {
            "kind": "clip",
            "source": item.get("source"),
            "start": _timeline_start(timeline, index),
            "end": _timeline_start(timeline, index) + _clip_duration(item),
            "effect": item.get("effect"),
            "params": {
                "source_start": item.get("start"),
                "source_end": item.get("end"),
                "speed": item.get("speed", 1.0),
                "transition": item.get("transition", "hard_cut"),
            },
        }
        for index, item in enumerate(timeline)
    ]

    skill_ids = {skill["skill_id"] for skill in applied_skills}
    tracks: list[dict[str, Any]] = [
        {
            "track_id": "main_video",
            "track_type": "video",
            "label": "主视频轨",
            "items": main_items,
        },
        {
            "track_id": "base_style",
            "track_type": "effect",
            "label": "底层风格轨",
            "items": [
                {
                    "kind": "effect",
                    "start": 0.0,
                    "end": target_duration,
                    "effect": _base_style_effect(skill_ids),
                    "params": {"opacity": 1.0},
                }
            ],
        },
    ]

    beat_effects = _beat_effect_items(beats, target_duration, skill_ids)
    if beat_effects:
        tracks.append(
            {
                "track_id": "beat_effect",
                "track_type": "effect",
                "label": "节拍效果轨",
                "items": beat_effects,
            }
        )

    overlay_items = _overlay_items(target_duration, skill_ids)
    if overlay_items:
        tracks.append(
            {
                "track_id": "overlay",
                "track_type": "overlay",
                "label": "包装/聚焦轨",
                "items": overlay_items,
            }
        )

    tracks.append(
        {
            "track_id": "audio",
            "track_type": "audio",
            "label": "音乐轨",
            "items": [{"kind": "audio", "start": 0.0, "end": target_duration, "effect": "bgm"}],
        }
    )
    return tracks


def _has_stage_like_clip(candidate_clips: list[dict]) -> bool:
    for clip in candidate_clips:
        usage = str(clip.get("recommended_usage", ""))
        atmosphere = float(clip.get("atmosphere_score", 0))
        stage_lighting = float(clip.get("stage_lighting_score", 0))
        tags = set(clip.get("visual_tags", []))
        if usage in {"beat_cut", "opening"} and (atmosphere >= 6.0 or stage_lighting >= 6.0 or "stage_color_pop" in tags):
            return True
    return False


def _has_transform_cue(reference_style: dict, candidate_clips: list[dict]) -> bool:
    if reference_style.get("flash_density", 0) >= 0.02:
        return True
    return any(clip.get("recommended_usage") == "transition" for clip in candidate_clips)


def _dedupe(skills: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    result = []
    for skill in skills:
        if skill["skill_id"] in seen:
            continue
        seen.add(skill["skill_id"])
        result.append(skill)
    return result


def _clip_duration(item: dict[str, Any]) -> float:
    raw_duration = max(0.1, float(item.get("end", 0)) - float(item.get("start", 0)))
    return raw_duration / max(0.2, float(item.get("speed", 1.0)))


def _timeline_start(timeline: list[dict[str, Any]], index: int) -> float:
    return round(sum(_clip_duration(item) for item in timeline[:index]), 2)


def _base_style_effect(skill_ids: set[str]) -> str:
    if "monochrome_to_color_beauty_reveal" in skill_ids:
        return "cool_white_face_glow"
    if "red_black_stage_tracking" in skill_ids:
        return "red_black_stage_grade"
    if "cool_white_beauty_closeup" in skill_ids:
        return "cool_white_soft_grade"
    return "balanced_beauty_grade"


def _beat_effect_items(beats: dict, target_duration: float, skill_ids: set[str]) -> list[dict[str, Any]]:
    if not ({"stage_beat_zoom_cut", "beat_keyframe_flash_focus"} & skill_ids):
        return []
    strong_beats = [float(beat) for beat in beats.get("strong_beats", []) if 0 < float(beat) < target_duration]
    if not strong_beats:
        strong_beats = [float(beat) for beat in beats.get("beats", [])[::4] if 0 < float(beat) < target_duration]
    items = []
    for index, beat in enumerate(strong_beats[:12]):
        effect = "flash_white" if index % 2 == 0 else "zoom_punch"
        items.append(
            {
                "kind": "effect",
                "start": round(max(0.0, beat - 0.04), 2),
                "end": round(min(target_duration, beat + 0.08), 2),
                "effect": effect,
                "params": {"strength": 0.7 if effect == "flash_white" else 0.45},
            }
        )
    return items


def _overlay_items(target_duration: float, skill_ids: set[str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if "black_fog_opening_reveal" in skill_ids:
        items.append(
            {
                "kind": "effect",
                "start": 0.0,
                "end": min(1.4, target_duration),
                "effect": "black_mask_reveal",
                "params": {"open_direction": "center_expand"},
            }
        )
    if "beat_keyframe_flash_focus" in skill_ids and target_duration > 4:
        items.append(
            {
                "kind": "effect",
                "start": round(target_duration * 0.55, 2),
                "end": round(min(target_duration, target_duration * 0.55 + 1.2), 2),
                "effect": "face_focus_glow",
                "params": {"vignette": True, "glow": "medium"},
            }
        )
    if "ending_freeze_memory" in skill_ids:
        items.append(
            {
                "kind": "effect",
                "start": round(max(0.0, target_duration - 1.0), 2),
                "end": round(target_duration, 2),
                "effect": "ending_freeze_soft_glow",
                "params": {"fade_out": True},
            }
        )
    return items
