import json
from collections import defaultdict
from typing import Any

from app.config import settings
from app.models.timeline_schema import TimelinePlan
from app.services.motion_transition_catalog import build_camera_instruction, build_transition_instruction
from app.services.skill_registry import build_tracks, select_skills


CAPTIONS = ["这一秒入坑", "", "镜头感拉满", "", "神颜名场面", "", "谁懂这一帧", ""]


def build_local_timeline(
    reference_style: dict,
    candidate_clips: list[dict],
    beats: dict,
    target_duration: int = 30,
) -> dict:
    clips = _ranked_clip_order(candidate_clips)
    if not clips:
        return _enrich_timeline(
            TimelinePlan(target_duration=target_duration, timeline=[]).model_dump(),
            reference_style,
            candidate_clips,
            beats,
        )
    if reference_style.get("edit_profile") == "contrast_two_video":
        contrast_timeline = _build_contrast_timeline(reference_style, clips, beats, target_duration)
        if contrast_timeline:
            return _enrich_timeline(contrast_timeline, reference_style, candidate_clips, beats)

    hero_clips = _hero_clip_pool(clips)
    beat_times = [0.0, *beats.get("beats", [])]
    strong_beats = [float(b) for b in beats.get("strong_beats", [])]
    avg_len = float(reference_style.get("avg_shot_duration", 1.2) or 1.2)
    min_len = _min_clip_length(reference_style)
    max_len = _max_clip_length(reference_style)
    timeline = []
    current = 0.0
    clip_index = 0
    used_keys: set[tuple[str, float, float]] = set()
    recent_sources: list[str] = []
    recent_effects: list[str] = []
    recent_transitions: list[str] = []
    recent_slow_motion_count = 0
    max_items = _max_timeline_items(reference_style, target_duration)

    while current < target_duration and clip_index < len(clips) * 4 and len(timeline) < max_items:
        next_beats = [float(b) for b in beat_times if float(b) > current + min_len]
        role = _timeline_role(current, target_duration)
        music_section = _music_section(current, target_duration)
        strong_candidates = [beat for beat in strong_beats if current + min_len <= beat <= current + max_len]
        if strong_candidates and (music_section == "drop" or role in {"transform_hit", "climax", "ending"}):
            end_at = strong_candidates[0]
        else:
            end_at = next_beats[0] if next_beats else min(target_duration, current + avg_len)
        desired = max(min_len, min(max_len, end_at - current))
        chosen = _choose_clip_for_role(clips, hero_clips, role, clip_index, used_keys, recent_sources, reference_style)
        clip_index += 1
        source_duration = max(0.6, float(chosen["end"]) - float(chosen["start"]))
        used = min(desired, source_duration)
        beat_hit = _is_strong_beat(end_at, strong_beats)
        speed = _speed_for_clip(chosen, role, beat_hit, reference_style)
        transition = _transition_for_clip(chosen, reference_style, beat_hit, role, len(timeline), music_section, recent_transitions)
        effect = _effect_for_clip(chosen, role, beat_hit, len(timeline), reference_style, music_section, recent_effects)
        speed, effect, slow_motion = _apply_slow_motion_policy(
            clip=chosen,
            role=role,
            beat_hit=beat_hit,
            music_section=music_section,
            current=current,
            base_speed=speed,
            effect=effect,
            reference_style=reference_style,
            recent_slow_motion_count=recent_slow_motion_count,
        )
        caption = _caption_for_item(len(timeline), role, reference_style)
        output_duration = used / speed
        visual_change_strength = _visual_change_strength(effect, transition, beat_hit, music_section)
        template_profile = reference_style.get("template_profile")
        camera_instruction = build_camera_instruction(effect, output_duration, len(timeline), template_profile)
        transition_instruction = build_transition_instruction(transition, len(timeline), template_profile) if transition != "hard_cut" and timeline else {}
        timeline.append(
            {
                "source": chosen["source"],
                "start": chosen["start"],
                "end": round(float(chosen["start"]) + used, 2),
                "speed": speed,
                "effect": effect,
                "transition": transition,
                "camera_instruction": camera_instruction,
                "transition_instruction": transition_instruction,
                "slow_motion": slow_motion,
                "caption": caption,
                "beat_align": True,
                "beat_hit": beat_hit,
                "music_section": music_section,
                "output_start": round(current, 3),
                "output_end": round(current + output_duration, 3),
                "visual_change_strength": visual_change_strength,
                "role": role,
                "shot_size": chosen.get("shot_size", "unknown"),
                "subject_position": chosen.get("subject_position", "unknown"),
                "crop_center": chosen.get("crop_center"),
            }
        )
        used_keys.add(_clip_key(chosen))
        recent_sources = _push_recent(recent_sources, str(chosen["source"]), 3)
        recent_effects = _push_recent(recent_effects, effect, 3)
        recent_transitions = _push_recent(recent_transitions, transition, 3)
        recent_slow_motion_count = recent_slow_motion_count + 1 if slow_motion.get("enabled") else 0
        current += output_duration

    return _enrich_timeline(
        TimelinePlan(
            title="这一秒直接入坑",
            style="饭圈颜值向智能剪辑",
            target_duration=min(target_duration, round(current, 2)),
            color_grade=reference_style.get("color_grade", "cool_white_soft"),
            timeline=timeline,
        ).model_dump(),
        reference_style,
        candidate_clips,
        beats,
    )


def _source_balanced_order(candidate_clips: list[dict]) -> list[dict]:
    by_source: dict[str, list[dict]] = defaultdict(list)
    for clip in candidate_clips:
        by_source[str(clip.get("source"))].append(clip)
    for source in by_source:
        by_source[source] = sorted(by_source[source], key=lambda c: c.get("highlight_score", 0), reverse=True)

    ordered_sources = sorted(by_source)
    ordered: list[dict] = []
    while any(by_source.values()):
        for source in ordered_sources:
            if by_source[source]:
                ordered.append(by_source[source].pop(0))
    return ordered


def _ranked_clip_order(candidate_clips: list[dict]) -> list[dict]:
    return sorted(candidate_clips, key=_beauty_score, reverse=True)


def _hero_clip_pool(clips: list[dict]) -> list[dict]:
    hero = [
        clip
        for clip in clips
        if clip.get("shot_size") in {"closeup", "medium_closeup", "half_body"}
        and clip.get("recommended_usage") not in {"fallback"}
    ]
    return (hero or clips)[: max(3, min(8, len(clips)))]


def _build_contrast_timeline(
    reference_style: dict,
    clips: list[dict],
    beats: dict,
    target_duration: int,
) -> dict[str, Any] | None:
    family_groups = _clips_by_source_family(clips)
    if len(family_groups) < 2:
        return None

    families = sorted(
        family_groups.items(),
        key=lambda item: sum(_beauty_score(clip) for clip in item[1]) / max(1, len(item[1])),
        reverse=True,
    )
    setup_family, reveal_family = families[-1][0], families[0][0]
    if setup_family == reveal_family and len(families) > 1:
        reveal_family = families[1][0]

    setup_clips = _hero_clip_pool(family_groups[setup_family]) or family_groups[setup_family]
    reveal_clips = _hero_clip_pool(family_groups[reveal_family]) or family_groups[reveal_family]
    beat_times = [0.0, *[float(b) for b in beats.get("beats", [])]]
    strong_beats = [float(b) for b in beats.get("strong_beats", [])]
    timeline: list[dict[str, Any]] = []
    current = 0.0
    recent_effects: list[str] = []
    recent_transitions: list[str] = []
    recent_slow_motion_count = 0
    max_items = min(24, max(10, int(target_duration / 0.85)))

    while current < target_duration and len(timeline) < max_items:
        progress = current / max(1.0, target_duration)
        if progress < 0.34:
            role = "contrast_setup_a"
            pool = setup_clips
            family_index = len([item for item in timeline if item.get("role") == role])
            desired_min, desired_max = 0.85, 1.4
        elif progress < 0.46:
            role = "contrast_bridge"
            pool = [setup_clips[-1], reveal_clips[0]]
            family_index = len(timeline)
            desired_min, desired_max = 0.45, 0.75
        elif progress < 0.84:
            role = "contrast_reveal_b"
            pool = reveal_clips
            family_index = len([item for item in timeline if item.get("role") == role])
            desired_min, desired_max = 0.55, 1.05
        else:
            role = "contrast_memory_lock"
            pool = reveal_clips
            family_index = len(timeline)
            desired_min, desired_max = 0.8, 1.4

        next_beats = [beat for beat in beat_times if beat > current + desired_min]
        end_at = next_beats[0] if next_beats else min(float(target_duration), current + desired_max)
        strong_candidates = [beat for beat in strong_beats if current + desired_min <= beat <= current + desired_max]
        if role in {"contrast_bridge", "contrast_reveal_b"} and strong_candidates:
            end_at = strong_candidates[0]
        desired = max(desired_min, min(desired_max, end_at - current))
        chosen = pool[family_index % len(pool)]
        source_duration = max(0.6, float(chosen["end"]) - float(chosen["start"]))
        used = min(desired, source_duration)
        beat_hit = _is_strong_beat(end_at, strong_beats) or role == "contrast_bridge"
        music_section = _music_section(current, target_duration)
        effect = _contrast_effect(role, beat_hit, recent_effects)
        transition = _contrast_transition(role, beat_hit, len(timeline), recent_transitions)
        speed = 1.0
        if role == "contrast_reveal_b" and beat_hit:
            speed = 1.12
        if role == "contrast_memory_lock":
            speed = 0.6
        speed, effect, slow_motion = _apply_slow_motion_policy(
            clip=chosen,
            role="climax" if role in {"contrast_reveal_b", "contrast_memory_lock"} else "transform_hit" if role == "contrast_bridge" else "setup",
            beat_hit=beat_hit,
            music_section="drop" if role in {"contrast_bridge", "contrast_reveal_b"} else music_section,
            current=current,
            base_speed=speed,
            effect=effect,
            reference_style=reference_style,
            recent_slow_motion_count=recent_slow_motion_count,
        )
        output_duration = used / speed
        template_profile = reference_style.get("template_profile")
        timeline.append(
            {
                "source": chosen["source"],
                "source_family": _source_family(str(chosen.get("source"))),
                "start": chosen["start"],
                "end": round(float(chosen["start"]) + used, 2),
                "speed": speed,
                "effect": effect,
                "transition": transition,
                "camera_instruction": build_camera_instruction(effect, output_duration, len(timeline), template_profile),
                "transition_instruction": build_transition_instruction(transition, len(timeline), template_profile) if transition != "hard_cut" and timeline else {},
                "slow_motion": slow_motion,
                "caption": "",
                "beat_align": True,
                "beat_hit": beat_hit,
                "music_section": "drop" if role in {"contrast_bridge", "contrast_reveal_b"} else music_section,
                "output_start": round(current, 3),
                "output_end": round(current + output_duration, 3),
                "visual_change_strength": _visual_change_strength(effect, transition, beat_hit, "drop" if role != "contrast_setup_a" else "build"),
                "role": role,
                "shot_size": chosen.get("shot_size", "unknown"),
                "subject_position": chosen.get("subject_position", "unknown"),
                "crop_center": chosen.get("crop_center"),
            }
        )
        recent_effects = _push_recent(recent_effects, effect, 3)
        recent_transitions = _push_recent(recent_transitions, transition, 3)
        recent_slow_motion_count = recent_slow_motion_count + 1 if slow_motion.get("enabled") else 0
        current += output_duration

    return TimelinePlan(
        title="Contrast Special",
        style="two source contrast edit",
        target_duration=min(target_duration, round(current, 2)),
        color_grade=reference_style.get("color_grade", "contrast_split_beauty"),
        timeline=timeline,
    ).model_dump()


def _clips_by_source_family(clips: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for clip in clips:
        groups[_source_family(str(clip.get("source", "")))].append(clip)
    for family in groups:
        groups[family] = sorted(groups[family], key=_beauty_score, reverse=True)
    return groups


def _source_family(source: str) -> str:
    if "_" in source:
        return source.split("_", 1)[1]
    return source


def _contrast_effect(role: str, beat_hit: bool, recent_effects: list[str]) -> str:
    if role == "contrast_setup_a":
        return _avoid_recent(["slow_zoom_in", "drift_zoom", "soft_glow"], recent_effects)
    if role == "contrast_bridge":
        return _avoid_recent(["zoom_punch", "snap_zoom", "whip_push"], recent_effects)
    if role == "contrast_reveal_b":
        return _avoid_recent(["snap_zoom", "zoom_punch", "beat_shake", "slowmo_beat_freeze"], recent_effects)
    return _avoid_recent(["slow_motion_glow", "breathing_zoom", "soft_glow"], recent_effects)


def _contrast_transition(role: str, beat_hit: bool, index: int, recent_transitions: list[str]) -> str:
    if index == 0:
        return "hard_cut"
    if role == "contrast_bridge":
        return _avoid_recent(["zoom_burst", "spin_blur", "whip_flash", "glow_flash"], recent_transitions)
    if role == "contrast_reveal_b" and beat_hit:
        return _avoid_recent(["zoom_burst", "shake_zoom", "spin_blur", "whip_flash"], recent_transitions)
    if role == "contrast_memory_lock":
        return _avoid_recent(["glow_flash", "soft_wash", "crossfade"], recent_transitions)
    return _avoid_recent(["soft_wash", "luma_fade", "hard_cut"], recent_transitions)


def _choose_clip_for_role(
    clips: list[dict],
    hero_clips: list[dict],
    role: str,
    offset: int,
    used_keys: set[tuple[str, float, float]],
    recent_sources: list[str],
    reference_style: dict,
) -> dict:
    preferred_clips = _preferred_clip_pool(hero_clips or clips, reference_style)
    if role in {"opening_hook", "transform_hit", "ending"}:
        return _choose_from_pool(preferred_clips, offset, used_keys, recent_sources, allow_reuse=True)
    if role == "climax" and offset % 2 == 0:
        return _choose_from_pool(preferred_clips, offset, used_keys, recent_sources, allow_reuse=True)
    return _choose_unused_clip(clips, offset, used_keys)


def _preferred_clip_pool(clips: list[dict], reference_style: dict) -> list[dict]:
    constraints = reference_style.get("frame_skill_constraints") or {}
    shot_priority = constraints.get("shot_priority") or []
    preferred_sizes = [value for value in shot_priority if value in {"closeup", "medium_closeup", "half_body", "full_body"}]
    if not preferred_sizes:
        return clips
    preferred = [clip for clip in clips if clip.get("shot_size") in preferred_sizes]
    if "center_or_near_center" in shot_priority:
        centered = [
            clip
            for clip in preferred
            if clip.get("subject_position") in {"center", "near_center", "upper_center"} or float(clip.get("composition_score", 0) or 0) >= 7
        ]
        preferred = centered or preferred
    return preferred or clips


def _choose_unused_clip(clips: list[dict], offset: int, used_keys: set[tuple[str, float, float]]) -> dict:
    for index in range(len(clips)):
        clip = clips[(offset + index) % len(clips)]
        if _clip_key(clip) not in used_keys:
            return clip
    return clips[offset % len(clips)]


def _choose_from_pool(
    clips: list[dict],
    offset: int,
    used_keys: set[tuple[str, float, float]],
    recent_sources: list[str],
    allow_reuse: bool,
) -> dict:
    fallback = clips[offset % len(clips)]
    for index in range(len(clips)):
        clip = clips[(offset + index) % len(clips)]
        source = str(clip.get("source"))
        if source in recent_sources:
            continue
        if allow_reuse or _clip_key(clip) not in used_keys:
            return clip
    for index in range(len(clips)):
        clip = clips[(offset + index) % len(clips)]
        if allow_reuse or _clip_key(clip) not in used_keys:
            return clip
    return fallback


def _beauty_score(clip: dict) -> float:
    score = float(clip.get("highlight_score", 0) or 0) * 1.45
    score += float(clip.get("face_ratio", 0) or 0) * 18
    score += float(clip.get("composition_score", 0) or 0) * 0.75
    score += float(clip.get("sharpness_score", 0) or 0) * 0.45
    score += float(clip.get("atmosphere_score", 0) or 0) * 0.25
    if clip.get("shot_size") in {"closeup", "medium_closeup"}:
        score += 2.2
    elif clip.get("shot_size") == "half_body":
        score += 1.1
    if clip.get("recommended_usage") in {"opening", "beauty_hold"}:
        score += 2.0
    if clip.get("recommended_usage") == "fallback":
        score -= 2.0
    return score


def _min_clip_length(reference_style: dict) -> float:
    if reference_style.get("min_shot_duration"):
        return float(reference_style["min_shot_duration"])
    if (reference_style.get("frame_skill_constraints") or {}).get("cut_strategy") == "stable_micro_progression":
        return 0.85
    if reference_style.get("edit_profile") == "monochrome_to_color_beauty":
        return 0.9
    if reference_style.get("cut_density") == "high" or reference_style.get("effect_intensity") == "strong":
        return 0.55
    if reference_style.get("motion_profile") == "slow_push":
        return 0.85
    return 0.7


def _max_clip_length(reference_style: dict) -> float:
    if reference_style.get("max_shot_duration"):
        return float(reference_style["max_shot_duration"])
    if (reference_style.get("frame_skill_constraints") or {}).get("cut_strategy") == "stable_micro_progression":
        return 2.6
    if reference_style.get("edit_profile") == "monochrome_to_color_beauty":
        return 2.4
    if reference_style.get("cut_density") == "high" or reference_style.get("climax_pattern") == "strong_beat_flash_zoom":
        return 1.75
    if reference_style.get("motion_profile") == "slow_push":
        return 2.8
    return 2.2


def _max_timeline_items(reference_style: dict, target_duration: float) -> int:
    profile_id = reference_style.get("template_profile_id") or reference_style.get("template")
    if profile_id in {"divine_beat", "stage"}:
        return min(30, max(14, int(target_duration / 0.85)))
    if profile_id in {"cinematic", "monochrome_beauty_reveal"}:
        return min(16, max(6, int(target_duration / 1.8)))
    if profile_id in {"korean_cool_white", "sweet", "progressive_idol_beauty"}:
        return min(22, max(8, int(target_duration / 1.15)))
    if reference_style.get("cut_density") == "high":
        return min(30, max(12, int(target_duration / 0.9)))
    return min(24, max(8, int(target_duration / 1.1)))


def _enrich_timeline(
    timeline_plan: dict[str, Any],
    reference_style: dict,
    candidate_clips: list[dict],
    beats: dict,
) -> dict[str, Any]:
    applied_skills = timeline_plan.get("applied_skills") or select_skills(reference_style, candidate_clips, beats)
    timeline_items = timeline_plan.get("timeline", [])
    timeline_items = _enforce_slow_motion_policy(timeline_items)
    timeline_plan["timeline"] = timeline_items
    target_duration = float(timeline_plan.get("target_duration") or 0)
    if timeline_items:
        target_duration = min(
            target_duration or 999,
            round(sum(max(0.1, float(item["end"]) - float(item["start"])) / max(0.2, float(item.get("speed", 1.0))) for item in timeline_items), 2),
        )
    if not target_duration:
        target_duration = float(beats.get("target_duration", 30))

    timeline_plan["applied_skills"] = applied_skills
    timeline_plan["tracks"] = timeline_plan.get("tracks") or build_tracks(timeline_items, applied_skills, beats, target_duration)
    timeline_plan["target_duration"] = target_duration
    timeline_plan["aspect_ratio"] = timeline_plan.get("aspect_ratio") or reference_style.get("aspect_ratio", "9:16")
    if reference_style.get("template_profile"):
        timeline_plan["template_profile"] = reference_style.get("template_profile")
    if reference_style.get("render_profile"):
        timeline_plan["render_profile"] = reference_style.get("render_profile")
    timeline_plan["style_fingerprint"] = _style_fingerprint(reference_style)
    timeline_plan["edit_decisions"] = _edit_decisions(timeline_items, reference_style)
    return timeline_plan


def _extract_json(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("LLM did not return JSON")
    return json.loads(text[start : end + 1])


def _style_fingerprint(reference_style: dict) -> dict[str, Any]:
    keys = [
        "template_profile_id",
        "template_profile_name",
        "opening_pattern",
        "climax_pattern",
        "motion_profile",
        "effect_intensity",
        "caption_frequency",
        "cut_density",
        "color_grade",
        "layout_profile",
        "aspect_ratio",
        "retrieved_preferred_style",
    ]
    return {key: reference_style.get(key) for key in keys if reference_style.get(key) is not None}


def _edit_decisions(timeline_items: list[dict], reference_style: dict) -> dict[str, Any]:
    hero_items = [item for item in timeline_items if item.get("role") in {"opening_hook", "transform_hit", "climax"}]
    decisions = {
        "hook_source": timeline_items[0].get("source") if timeline_items else None,
        "hero_sources": sorted({str(item.get("source")) for item in hero_items if item.get("source")})[:5],
        "motion_strategy": reference_style.get("motion_profile", "slow_push"),
        "effect_strategy": reference_style.get("effect_intensity", "medium"),
        "caption_strategy": reference_style.get("caption_frequency", "low"),
        "climax_strategy": reference_style.get("climax_pattern", "beauty_flash_hold"),
        "music_strategy": "intro/build/drop/outro 分段，强拍集中冲击，普通拍减少重复闪白",
    }
    retrieved = _retrieved_skill_strategy(reference_style)
    if retrieved:
        decisions["retrieved_skill_strategy"] = retrieved
    return decisions


def generate_timeline(
    reference_style: dict,
    candidate_clips: list[dict],
    beats: dict,
    target_duration: int = 30,
    use_llm: bool = True,
) -> dict:
    sources = {str(clip.get("source")) for clip in candidate_clips}
    if len(sources) > 1:
        return build_local_timeline(reference_style, candidate_clips, beats, target_duration)
    if not use_llm or not settings.openai_api_key:
        return build_local_timeline(reference_style, candidate_clips, beats, target_duration)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        payload = {
            "reference_style": reference_style,
            "candidate_clips": candidate_clips[:80],
            "beats": beats,
            "target_duration": target_duration,
            "slow_motion_policy": {
                "allowed_triggers": ["strong_beat", "melody_soft_turn", "emotion_turn", "dance_pose_hold", "face_closeup_highlight", "stage_highlight"],
                "max_consecutive": 2,
                "must_separate_with_normal_speed": True,
                "forbidden": ["opening", "transition_gap", "wide_shot", "long_running_movement"],
                "speed_ranges": {"lyrical_soft": "0.5-0.7", "beat_highlight": "0.3-0.4"},
                "forbidden_speed_ranges": ["<0.2", "0.8-0.9"],
                "subject_lock": ["face", "upper_body_closeup"],
                "camera_constraint": "slow_camera_only_no_whip_no_shake_no_fast_push_pull",
            },
        }
        prompt = f"""
你是一个饭圈颜值向剪辑师。请根据候选镜头、参考风格和 BGM 节拍生成 9:16 竖屏颜值向卡点混剪 timeline。只输出严格 JSON，不要解释文字。
要求：每个镜头 0.6-2.5 秒，切点贴合 beat，字幕少量，不改变人物脸部结构。
输入 JSON：{json.dumps(payload, ensure_ascii=False)}
"""
        aspect_ratio = str(reference_style.get("aspect_ratio") or "9:16")
        prompt = (
            f"你是一个饭圈颜值向剪辑师。请根据候选镜头、参考风格和 BGM 节拍生成 {aspect_ratio} 画幅的颜值向卡点混剪 timeline。"
            "只输出严格 JSON，不要解释文字。\n"
            f"要求：每个镜头 0.6-2.5 秒，切点贴合 beat，字幕少量，不改变人物脸部结构，裁切和运镜需要适配 {aspect_ratio} 画幅。\n"
            f"输入 JSON：{json.dumps(payload, ensure_ascii=False)}"
        )
        prompt += (
            "\nSlow motion hard policy: use slow motion only on rhythm or emotion turning points. "
            "Max 2 consecutive slow clips, with normal-speed separation afterward. "
            "Never slow down opening, transition gaps, wide shots, or long running movement. "
            "Allowed speeds are 0.5-0.7 for lyrical soft moments and 0.3-0.4 for beat highlights. "
            "Never use speeds below 0.2 or weak slow speeds 0.8-0.9. "
            "Slow motion must lock face or upper-body closeups and use slow camera movement only."
        )
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.45,
        )
        data = _extract_json(response.choices[0].message.content or "{}")
        return _enrich_timeline(TimelinePlan(**data).model_dump(), reference_style, candidate_clips, beats)
    except Exception:
        return build_local_timeline(reference_style, candidate_clips, beats, target_duration)


def _timeline_role(current: float, target_duration: float) -> str:
    progress = current / max(1.0, target_duration)
    if current < 3:
        return "opening_hook"
    if progress < 0.35:
        return "setup"
    if progress < 0.48:
        return "pre_transform"
    if progress < 0.58:
        return "transform_hit"
    if progress < 0.86:
        return "climax"
    return "ending"


def _clip_key(clip: dict) -> tuple[str, float, float]:
    return (str(clip.get("source")), round(float(clip.get("start", 0)), 2), round(float(clip.get("end", 0)), 2))


def _is_strong_beat(time_sec: float, strong_beats: list[float]) -> bool:
    return any(abs(time_sec - beat) <= 0.12 for beat in strong_beats)


def _music_section(current: float, target_duration: float) -> str:
    progress = current / max(1.0, target_duration)
    if progress < 0.18:
        return "intro"
    if progress < 0.46:
        return "build"
    if progress < 0.82:
        return "drop"
    return "outro"


def _push_recent(items: list[str], value: str, limit: int) -> list[str]:
    return [*items, value][-limit:]


def _speed_for_clip(clip: dict, role: str, beat_hit: bool, reference_style: dict) -> float:
    intensity = reference_style.get("effect_intensity", "medium")
    if role == "opening_hook":
        return 1.0
    if role == "ending":
        return 1.0
    if role in {"transform_hit", "climax"} and beat_hit:
        return 1.16 if intensity == "strong" else 1.1
    if role == "pre_transform":
        return 1.04
    return 1.0


def _apply_slow_motion_policy(
    clip: dict,
    role: str,
    beat_hit: bool,
    music_section: str,
    current: float,
    base_speed: float,
    effect: str,
    reference_style: dict,
    recent_slow_motion_count: int,
) -> tuple[float, str, dict[str, Any]]:
    if not _slow_motion_allowed(clip, role, beat_hit, music_section, current, recent_slow_motion_count):
        return _normalize_non_slow_speed(base_speed), effect, _slow_motion_meta(False, "not_allowed")

    intensity = reference_style.get("effect_intensity", "medium")
    edit_profile = reference_style.get("edit_profile", "")
    is_soft_style = intensity in {"subtle", "medium"} or edit_profile in {"slow_mood_beauty", "monochrome_to_color_beauty"}
    if beat_hit and (role in {"transform_hit", "climax"} or music_section == "drop") and intensity == "strong":
        return 0.35, "slowmo_beat_freeze", _slow_motion_meta(
            True,
            "beat_turning_point",
            speed_range="0.3-0.4",
            render_priority=["face_highlight", "hair_rim_light", "flash_or_sparkle", "1-2_frame_freeze_rebound"],
        )
    if role in {"transform_hit", "climax", "ending"} and is_soft_style:
        return 0.6, "slow_motion_glow", _slow_motion_meta(
            True,
            "lyrical_or_emotional_turn",
            speed_range="0.5-0.7",
            render_priority=["face_highlight", "hair_rim_light", "soft_glow", "light_background_blur"],
        )
    return _normalize_non_slow_speed(base_speed), effect, _slow_motion_meta(False, "trigger_not_strong_enough")


def _slow_motion_allowed(
    clip: dict,
    role: str,
    beat_hit: bool,
    music_section: str,
    current: float,
    recent_slow_motion_count: int,
) -> bool:
    if current < 3.0 or role in {"opening_hook", "setup", "pre_transform"}:
        return False
    if recent_slow_motion_count >= 2:
        return False
    if clip.get("recommended_usage") == "transition":
        return False
    shot_size = clip.get("shot_size")
    if shot_size not in {"closeup", "medium_closeup", "half_body"}:
        return False
    motion_energy = str(clip.get("motion_energy", "unknown"))
    if motion_energy == "high" and shot_size not in {"closeup", "medium_closeup"}:
        return False
    face_ratio = float(clip.get("face_ratio", 0) or 0)
    if face_ratio <= 0.015 and shot_size != "half_body":
        return False
    return beat_hit or role in {"transform_hit", "ending"} or music_section in {"drop", "outro"}


def _normalize_non_slow_speed(speed: float) -> float:
    if 0.8 <= speed < 1.0:
        return 1.0
    if 0.2 <= speed < 0.5:
        return 0.5
    return speed


def _slow_motion_meta(
    enabled: bool,
    trigger: str,
    speed_range: str | None = None,
    render_priority: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "enabled": enabled,
        "trigger": trigger,
        "speed_range": speed_range,
        "rules": {
            "max_consecutive_segments": 2,
            "forbidden_sections": ["opening", "transition_gap", "wide_running_movement"],
            "subject_lock": ["face", "upper_body_closeup"],
            "forbidden_speed_ranges": ["<0.2", "0.8-0.9"],
        },
        "render_priority": render_priority or [],
    }


def _enforce_slow_motion_policy(items: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    consecutive_slow = 0
    for index, raw in enumerate(items):
        item = dict(raw)
        speed = _safe_float(item.get("speed", 1.0), 1.0)
        slow_meta = dict(item.get("slow_motion") or {})
        is_slow = bool(slow_meta.get("enabled")) or speed < 0.8
        if not is_slow:
            item["speed"] = _normalize_non_slow_speed(speed)
            item["slow_motion"] = slow_meta or _slow_motion_meta(False, "normal_speed")
            consecutive_slow = 0
            normalized.append(item)
            continue

        allowed = _timeline_item_slow_allowed(item, index, consecutive_slow)
        if not allowed:
            item["speed"] = 1.0
            item["slow_motion"] = _slow_motion_meta(False, "policy_sanitized")
            consecutive_slow = 0
            normalized.append(item)
            continue

        if speed < 0.2:
            speed = 0.35
        elif 0.4 < speed < 0.5:
            speed = 0.5
        elif 0.7 < speed < 1.0:
            speed = 0.6
        item["speed"] = speed
        item["slow_motion"] = {
            **_slow_motion_meta(True, slow_meta.get("trigger") or "turning_point", slow_meta.get("speed_range"), slow_meta.get("render_priority") or []),
            **slow_meta,
            "enabled": True,
        }
        if item.get("effect") in {"zoom_punch", "snap_zoom", "beat_shake", "whip_push"}:
            item["effect"] = "slowmo_beat_freeze" if speed <= 0.4 else "slow_motion_glow"
        consecutive_slow += 1
        normalized.append(item)
    return normalized


def _timeline_item_slow_allowed(item: dict, index: int, consecutive_slow: int) -> bool:
    if index == 0 or consecutive_slow >= 2:
        return False
    if item.get("role") in {"opening_hook", "setup", "pre_transform"} or item.get("music_section") == "intro":
        return False
    if item.get("shot_size") not in {"closeup", "medium_closeup", "half_body"}:
        return False
    return bool(item.get("beat_hit") or item.get("role") in {"transform_hit", "climax", "ending"} or item.get("music_section") in {"drop", "outro"})


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _transition_for_clip(
    clip: dict,
    reference_style: dict,
    beat_hit: bool,
    role: str,
    index: int,
    music_section: str,
    recent_transitions: list[str],
) -> str:
    intensity = reference_style.get("effect_intensity", "medium")
    climax_pattern = reference_style.get("climax_pattern", "")
    constraints = reference_style.get("frame_skill_constraints") or {}
    preferred_transitions = constraints.get("preferred_transitions") or []
    preferred_transitions = [value for value in preferred_transitions if value != "hard_cut"]
    template_transition = (reference_style.get("template_profile") or {}).get("transition") or {}
    template_preferred = [value for value in template_transition.get("preferred", []) if value != "hard_cut"]
    template_avoid = set(template_transition.get("avoid", []))
    if index == 0:
        return "hard_cut"
    if preferred_transitions and role in {"transform_hit", "climax", "ending"}:
        return _avoid_recent([*preferred_transitions, "zoom_burst", "spin_blur", "bloom_blur", "whip_pan", "soft_wash"], recent_transitions)
    if template_preferred:
        if music_section in {"intro", "outro"}:
            soft_options = [
                value
                for value in template_preferred
                if value not in {"strobe_white", "shake_zoom", "spin_blur", "whip_pan", "zoom_burst"} and value not in template_avoid
            ]
            if soft_options:
                return _avoid_recent(soft_options, recent_transitions)
        if beat_hit or role in {"transform_hit", "climax"}:
            return _avoid_recent([value for value in template_preferred if value not in template_avoid], recent_transitions)
    if beat_hit and music_section == "drop":
        return _avoid_recent(["zoom_burst", "shake_zoom", "spin_blur", "whip_pan", "bloom_blur", "glow_flash"], recent_transitions)
    if reference_style.get("edit_profile") == "monochrome_to_color_beauty":
        return _avoid_recent(["luma_fade", "soft_wash", "crossfade", "glow_flash"], recent_transitions)
    if music_section in {"intro", "outro"} and role not in {"transform_hit"}:
        return _avoid_recent(["soft_wash", "luma_fade", "hard_cut"], recent_transitions)
    if role == "transform_hit":
        return _avoid_recent(["zoom_burst", "rotate_flash", "bloom_blur", "whip_pan", "glow_flash"], recent_transitions)
    if role == "climax" and beat_hit and intensity == "strong":
        return _avoid_recent(["shake_zoom", "zoom_burst", "spin_blur", "whip_pan", "bloom_blur"], recent_transitions)
    if role == "climax" and beat_hit and climax_pattern == "beauty_flash_hold":
        return _avoid_recent(["glow_flash", "bloom_blur", "soft_wash"], recent_transitions)
    if role == "pre_transform" and index % 4 == 0:
        return "luma_fade"
    if beat_hit and "flash_white" in reference_style.get("transition_style", []):
        return "flash_white"
    if role == "ending" and "crossfade" in reference_style.get("transition_style", []):
        return "crossfade"
    if clip.get("recommended_usage") == "transition":
        return "flash_white"
    return "hard_cut"


def _effect_for_clip(
    clip: dict,
    role: str,
    beat_hit: bool,
    index: int,
    reference_style: dict,
    music_section: str,
    recent_effects: list[str],
) -> str:
    motion_profile = reference_style.get("motion_profile", "slow_push")
    intensity = reference_style.get("effect_intensity", "medium")
    constraints = reference_style.get("frame_skill_constraints") or {}
    mapped_role = _frame_skill_role(role, music_section)
    mapped_effects = (constraints.get("effect_mapping") or {}).get(mapped_role, [])
    preferred_effects = constraints.get("preferred_effects") or []
    if beat_hit and music_section == "drop":
        return _avoid_recent(["zoom_punch", "snap_zoom", "whip_push", *mapped_effects, *preferred_effects], recent_effects)
    if mapped_effects:
        return _avoid_recent([*mapped_effects, *preferred_effects], recent_effects)
    if reference_style.get("edit_profile") == "monochrome_to_color_beauty":
        if music_section == "intro":
            return _avoid_recent(["mono_mystery", "soft_blur_reveal", "micro_push"], recent_effects)
        if music_section == "build":
            return _avoid_recent(["clarity_rise", "desaturate_to_color", "micro_push"], recent_effects)
        if music_section == "drop":
            return _avoid_recent(["cool_white_face_glow", "breathing_zoom", "hair_rim_light"], recent_effects)
        return _avoid_recent(["beauty_freeze", "cool_white_face_glow", "micro_push"], recent_effects)
    if music_section == "intro":
        return _avoid_recent(["slow_zoom_in", "drift_zoom", "soft_glow"], recent_effects)
    if music_section == "outro":
        return _avoid_recent(["drift_zoom", "slow_zoom_in", "soft_glow"], recent_effects)
    if role == "transform_hit":
        if intensity == "strong":
            return _avoid_recent(["snap_zoom", "zoom_punch", "whip_push"], recent_effects)
        return "zoom_punch"
    if role in {"opening_hook", "ending"}:
        if motion_profile == "gentle_drift":
            return "drift_zoom"
        return "slow_zoom_in" if index % 2 == 0 else "drift_zoom"
    if role == "climax" and beat_hit:
        if intensity == "strong":
            return _avoid_recent(["zoom_punch", "beat_shake", "whip_push", "snap_zoom"], recent_effects)
        return "zoom_punch" if intensity == "medium" else "soft_glow"
    if role in {"setup", "pre_transform"}:
        if motion_profile == "slow_push":
            return _avoid_recent(["slow_zoom_in", "drift_zoom", "soft_glow"], recent_effects)
        return _avoid_recent(["pan_left", "pan_right", "tilt_up", "drift_zoom"], recent_effects)
    if clip.get("shot_size") in {"closeup", "medium_closeup"}:
        return "soft_glow"
    return "slight_zoom"


def _avoid_recent(options: list[str], recent_values: list[str]) -> str:
    for option in options:
        if option not in recent_values:
            return option
    return options[0]


def _visual_change_strength(effect: str, transition: str, beat_hit: bool, music_section: str) -> float:
    effect_weight = {
        "mono_mystery": 0.35,
        "soft_blur_reveal": 0.35,
        "clarity_rise": 0.55,
        "desaturate_to_color": 0.6,
        "cool_white_face_glow": 0.45,
        "breathing_zoom": 0.4,
        "hair_rim_light": 0.45,
        "beauty_freeze": 0.5,
        "zoom_punch": 0.78,
        "snap_zoom": 0.85,
        "beat_shake": 0.9,
        "whip_push": 0.88,
        "slow_zoom_in": 0.32,
        "drift_zoom": 0.34,
        "soft_glow": 0.34,
        "slight_zoom": 0.22,
    }.get(effect, 0.3)
    transition_weight = {
        "hard_cut": 0.08,
        "crossfade": 0.2,
        "glow_flash": 0.28,
        "flash_white": 0.34,
        "flash_black": 0.28,
        "whip_flash": 0.38,
        "strobe_white": 0.42,
        "soft_wash": 0.32,
        "bloom_blur": 0.46,
        "whip_pan": 0.52,
        "luma_fade": 0.3,
        "zoom_burst": 0.56,
        "spin_blur": 0.58,
        "rotate_flash": 0.54,
        "shake_zoom": 0.6,
    }.get(transition, 0.12)
    beat_bonus = 0.12 if beat_hit else 0.0
    section_bonus = 0.08 if music_section == "drop" else 0.0
    return round(min(1.0, effect_weight + transition_weight + beat_bonus + section_bonus), 3)


def _frame_skill_role(role: str, music_section: str) -> str:
    if role == "opening_hook" or music_section == "intro":
        return "atmosphere_setup"
    if role in {"setup", "pre_transform"} or music_section == "build":
        return "reveal_transition"
    if role in {"transform_hit", "climax"} or music_section == "drop":
        return "core_visual_hold"
    return "memory_point"


def _retrieved_skill_strategy(reference_style: dict) -> dict[str, Any]:
    constraints = reference_style.get("frame_skill_constraints") or {}
    if not constraints:
        return {}
    return {
        "opening_strategy": constraints.get("opening_strategy"),
        "motion_strategy": constraints.get("motion_strategy"),
        "cut_strategy": constraints.get("cut_strategy"),
        "shot_priority": constraints.get("shot_priority"),
        "preferred_style_template": constraints.get("preferred_style_template"),
        "human_preference_strength": constraints.get("human_preference_strength"),
    }


def _caption_for_item(index: int, role: str, reference_style: dict) -> str:
    frequency = reference_style.get("caption_frequency", "low")
    if index == 0:
        return CAPTIONS[0]
    if frequency == "medium" and role in {"opening_hook", "transform_hit", "climax"} and index % 4 == 2:
        return CAPTIONS[index % len(CAPTIONS)]
    if frequency == "low" and index in {2, 6}:
        return CAPTIONS[index % len(CAPTIONS)]
    return ""
