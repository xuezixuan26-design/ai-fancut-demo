import json
from typing import Any

from app.config import settings
from app.models.timeline_schema import TimelinePlan


CAPTIONS = ["这一秒入坑", "", "镜头感拉满", "", "神颜名场面", "", "谁懂这一帧", ""]


def build_local_timeline(
    reference_style: dict,
    candidate_clips: list[dict],
    beats: dict,
    target_duration: int = 30,
) -> dict:
    clips = sorted(candidate_clips, key=lambda c: c["highlight_score"], reverse=True)
    if not clips:
        return TimelinePlan(target_duration=target_duration, timeline=[]).model_dump()

    beat_times = [0.0, *beats.get("beats", [])]
    strong_beats = set(round(b, 3) for b in beats.get("strong_beats", []))
    avg_len = float(reference_style.get("avg_shot_duration", 1.2) or 1.2)
    min_len = 0.7
    max_len = 2.4
    timeline = []
    current = 0.0
    clip_index = 0
    last_source = ""

    while current < target_duration and clip_index < len(clips) * 3:
        next_beats = [b for b in beat_times if b > current + min_len]
        end_at = next_beats[0] if next_beats else min(target_duration, current + avg_len)
        desired = max(min_len, min(max_len, end_at - current))
        ranked = clips[clip_index % len(clips) :] + clips[: clip_index % len(clips)]
        chosen = next((c for c in ranked if c["source"] != last_source), ranked[0])
        clip_index += 1
        source_duration = max(0.6, chosen["end"] - chosen["start"])
        used = min(desired, source_duration)
        speed = 0.85 if chosen["highlight_score"] >= 8.0 and round(end_at, 3) in strong_beats else 1.0
        transition = "flash_white" if round(end_at, 3) in strong_beats and "flash_white" in reference_style.get("transition_style", []) else "hard_cut"
        effect = "slow_zoom_in" if chosen["recommended_usage"] == "opening" or chosen["highlight_score"] >= 8.0 else "slight_zoom"
        caption = CAPTIONS[len(timeline) % len(CAPTIONS)] if len(timeline) in {0, 2, 4, 6} else ""
        timeline.append(
            {
                "source": chosen["source"],
                "start": chosen["start"],
                "end": round(chosen["start"] + used, 2),
                "speed": speed,
                "effect": effect,
                "transition": transition,
                "caption": caption,
                "beat_align": True,
            }
        )
        current += used / speed
        last_source = chosen["source"]

    return TimelinePlan(
        target_duration=min(target_duration, round(current, 2)),
        color_grade=reference_style.get("color_grade", "cool_white_soft"),
        timeline=timeline,
    ).model_dump()


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
你是一个饭圈颜值向剪辑师。请根据候选镜头和 BGM 节拍生成一条 9:16 竖屏颜值向卡点混剪时间线。
只输出严格 JSON，不要解释文字。
要求：
- 成片 20-45 秒。
- 开头 3 秒必须使用高分近景镜头。
- 高潮或强拍处使用最高分镜头。
- 镜头切换尽量贴合 beat。
- 每个镜头 0.6-2.5 秒。
- 不要连续使用太多同一视频来源。
- 可以使用 slow_zoom_in、slight_zoom、soft_glow、freeze_frame。
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
        return TimelinePlan(**data).model_dump()
    except Exception:
        return build_local_timeline(reference_style, candidate_clips, beats, target_duration)
