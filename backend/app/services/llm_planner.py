import json
from typing import Any

from app.config import settings
from app.models.timeline_schema import TimelinePlan
from app.services.skill_registry import build_tracks, select_skills


CAPTIONS = ["这一秒入坑", "", "镜头感拉满", "", "神颜名场面", "", "谁懂这一帧", ""]


def build_local_timeline(
    reference_style: dict,
    candidate_clips: list[dict],
    beats: dict,
    target_duration: int = 30,
) -> dict:
    clips = sorted(candidate_clips, key=lambda c: c["highlight_score"], reverse=True)
    if not clips:
        return _enrich_timeline(
            TimelinePlan(target_duration=target_duration, timeline=[]).model_dump(),
            reference_style,
            candidate_clips,
            beats,
        )

    beat_times = [0.0, *beats.get("beats", [])]
    strong_beats = set(round(float(b), 3) for b in beats.get("strong_beats", []))
    avg_len = float(reference_style.get("avg_shot_duration", 1.2) or 1.2)
    min_len = 0.65 if reference_style.get("cut_density") == "high" else 0.8
    max_len = 2.2 if reference_style.get("cut_density") == "high" else 2.6
    timeline = []
    current = 0.0
    clip_index = 0
    last_source = ""

    while current < target_duration and clip_index < len(clips) * 4:
        next_beats = [float(b) for b in beat_times if float(b) > current + min_len]
        end_at = next_beats[0] if next_beats else min(target_duration, current + avg_len)
        desired = max(min_len, min(max_len, end_at - current))
        role = _timeline_role(current, target_duration)
        chosen = _choose_clip(clips, role, last_source, clip_index)
        clip_index += 1
        source_duration = max(0.6, float(chosen["end"]) - float(chosen["start"]))
        used = min(desired, source_duration)
        beat_hit = round(end_at, 3) in strong_beats
        speed = _speed_for_clip(chosen, role, beat_hit)
        transition = _transition_for_clip(chosen, reference_style, beat_hit, role)
        effect = _effect_for_clip(chosen, role, beat_hit)
        caption = CAPTIONS[len(timeline) % len(CAPTIONS)] if len(timeline) in {0, 2, 4, 6} else ""
        timeline.append(
            {
                "source": chosen["source"],
                "start": chosen["start"],
                "end": round(float(chosen["start"]) + used, 2),
                "speed": speed,
                "effect": effect,
                "transition": transition,
                "caption": caption,
                "beat_align": True,
                "role": role,
                "shot_size": chosen.get("shot_size", "unknown"),
                "subject_position": chosen.get("subject_position", "unknown"),
            }
        )
        current += used / speed
        last_source = chosen["source"]

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


def _enrich_timeline(
    timeline_plan: dict[str, Any],
    reference_style: dict,
    candidate_clips: list[dict],
    beats: dict,
) -> dict[str, Any]:
    applied_skills = timeline_plan.get("applied_skills") or select_skills(reference_style, candidate_clips, beats)
    timeline_items = timeline_plan.get("timeline", [])
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
    return timeline_plan


def _extract_json(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("LLM did not return JSON")
    return json.loads(text[start : end + 1])


def generate_timeline(
    reference_style: dict,
    candidate_clips: list[dict],
    beats: dict,
    target_duration: int = 30,
    use_llm: bool = True,
) -> dict:
    if not use_llm or not settings.openai_api_key:
        return build_local_timeline(reference_style, candidate_clips, beats, target_duration)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        payload = {
            "reference_style": reference_style,
            "candidate_clips": candidate_clips[:40],
            "beats": beats,
            "target_duration": target_duration,
        }
        prompt = f"""
你是一个饭圈颜值向剪辑师。请根据候选镜头、参考风格和 BGM 节拍生成 9:16 竖屏颜值向卡点混剪 timeline。
只输出严格 JSON，不要解释文字。

剪辑要求：
- 成片 20-45 秒。
- 开头 3 秒必须用高分近景/特写/半身片段抓人。
- timeline item 尽量标出 role：opening_hook、setup、pre_transform、transform_hit、climax、ending。
- 高潮或强拍处使用最高分镜头，切点尽量贴合 beat。
- 每个镜头 0.6-2.5 秒，不要连续使用太多同一视频来源。
- 可使用 effect：slow_zoom_in、slight_zoom、soft_glow、freeze_frame、zoom_punch。
- transition 只能使用 hard_cut、flash_white、crossfade。
- 字幕少量，偏饭圈安利/氛围感。
- 不要改变人物脸部结构，不要美颜重塑。

输入 JSON：
{json.dumps(payload, ensure_ascii=False)}
"""
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.5,
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


def _choose_clip(clips: list[dict], role: str, last_source: str, offset: int) -> dict:
    preferred_usage = {
        "opening_hook": {"opening", "beauty_hold"},
        "setup": {"beauty_hold", "supporting", "beat_cut"},
        "pre_transform": {"beauty_hold", "supporting"},
        "transform_hit": {"beat_cut", "transition", "opening"},
        "climax": {"beat_cut", "opening", "beauty_hold"},
        "ending": {"beauty_hold", "opening"},
    }.get(role, {"beat_cut"})
    ranked = clips[offset % len(clips) :] + clips[: offset % len(clips)]
    usage_match = [clip for clip in ranked if clip.get("recommended_usage") in preferred_usage and clip.get("source") != last_source]
    if usage_match:
        return max(usage_match, key=lambda c: c.get("highlight_score", 0))
    source_match = [clip for clip in ranked if clip.get("source") != last_source]
    return source_match[0] if source_match else ranked[0]


def _speed_for_clip(clip: dict, role: str, beat_hit: bool) -> float:
    if role in {"opening_hook", "ending"} and clip.get("recommended_usage") in {"opening", "beauty_hold"}:
        return 0.9
    if role in {"transform_hit", "climax"} and beat_hit:
        return 1.08
    return 1.0


def _transition_for_clip(clip: dict, reference_style: dict, beat_hit: bool, role: str) -> str:
    if role == "transform_hit":
        return "flash_white"
    if beat_hit and "flash_white" in reference_style.get("transition_style", []):
        return "flash_white"
    if role == "ending" and "crossfade" in reference_style.get("transition_style", []):
        return "crossfade"
    if clip.get("recommended_usage") == "transition":
        return "flash_white"
    return "hard_cut"


def _effect_for_clip(clip: dict, role: str, beat_hit: bool) -> str:
    if role == "transform_hit":
        return "zoom_punch"
    if role in {"opening_hook", "ending"}:
        return "slow_zoom_in"
    if role == "climax" and beat_hit:
        return "zoom_punch"
    if clip.get("shot_size") in {"closeup", "medium_closeup"}:
        return "soft_glow"
    return "slight_zoom"
