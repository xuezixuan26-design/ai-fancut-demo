from pathlib import Path
from typing import Any
import base64
import json

import cv2
import numpy as np

from app.config import settings
from app.services.face_analyzer import FaceAnalyzer
from app.services.knowledge_base import upsert_frame_to_edit_skill
from app.utils.file_utils import project_dir
from app.utils.json_utils import write_json


FRAME_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def analyze_frame_directory(
    frame_dir: str,
    project_id: str | None = None,
    sample_limit: int = 12,
    use_ai: bool = False,
) -> dict[str, Any]:
    path = _validate_frame_dir(frame_dir)
    frames = _frame_paths(path, sample_limit)
    if not frames:
        raise ValueError("No frame images found in the selected directory.")

    face_analyzer = FaceAnalyzer()
    frame_features = []
    previous_small = None
    for index, frame_path in enumerate(frames):
        frame = cv2.imread(str(frame_path))
        if frame is None:
            continue
        features, small_gray = _extract_frame_features(frame, frame_path.name, index, len(frames), face_analyzer)
        if previous_small is not None:
            features["frame_diff"] = round(float(np.mean(cv2.absdiff(previous_small, small_gray))), 3)
        else:
            features["frame_diff"] = None
        features["edit_role"] = _frame_role(index, len(frames), features)
        features["edit_hint"] = _frame_edit_hint(index, len(frames), features)
        frame_features.append(features)
        previous_small = small_gray

    relations = _build_relations(frame_features)
    windows = _build_windows(frame_features, [5, 8])
    skill = _distill_skill(frame_features, relations, windows)
    ai_analysis = _run_multimodal_analysis(path, frames, skill) if use_ai and settings.openai_api_key else None
    result = {
        "schema": "ai-fancut.frame-to-edit-analysis.v1",
        "project_id": project_id,
        "frame_dir": str(path),
        "frame_count": len(frame_features),
        "sample_limit": sample_limit,
        "ai_status": _ai_status(use_ai, ai_analysis),
        "ai_analysis": ai_analysis,
        "frames": frame_features,
        "relations": relations,
        "windows": windows,
        "learned_skill": skill,
        "multimodal_prompt": _multimodal_prompt(skill),
    }

    output_path = project_dir(project_id) / "frame_to_edit_analysis.json" if project_id else path / "frame_to_edit_analysis.json"
    write_json(output_path, result)
    upsert_frame_to_edit_skill(result)
    result["saved_to"] = str(output_path)
    return result


def _validate_frame_dir(frame_dir: str) -> Path:
    path = Path(frame_dir).expanduser().resolve()
    allowed_roots = [
        settings.root_dir.resolve(),
        settings.root_dir.parent.resolve(),
        settings.storage_dir.resolve(),
    ]
    if not path.exists() or not path.is_dir():
        raise ValueError(f"Frame directory not found: {path}")
    if not any(path == root or root in path.parents for root in allowed_roots):
        raise ValueError("Frame directory must be inside the current workspace or its parent folder.")
    return path


def _frame_paths(path: Path, sample_limit: int) -> list[Path]:
    all_frames = sorted(
        item
        for item in path.iterdir()
        if item.is_file() and item.suffix.lower() in FRAME_EXTS and "contact_sheet" not in item.name.lower()
    )
    limit = max(1, min(int(sample_limit or 12), 40))
    if len(all_frames) <= limit:
        return all_frames
    indexes = np.linspace(0, len(all_frames) - 1, limit).round().astype(int)
    return [all_frames[int(i)] for i in indexes]


def _extract_frame_features(
    frame: np.ndarray,
    name: str,
    index: int,
    total: int,
    face_analyzer: FaceAnalyzer,
) -> tuple[dict[str, Any], np.ndarray]:
    h, w = frame.shape[:2]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    face = face_analyzer.detect_face(frame)
    brightness = float(np.mean(gray))
    saturation = float(np.mean(hsv[:, :, 1]))
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    contrast = float(np.std(gray))
    center = face.center or (0.5, 0.48)
    face_ratio = float(face.ratio or 0.0)
    progress = index / max(1, total - 1)
    small_gray = cv2.resize(gray, (64, 96), interpolation=cv2.INTER_AREA)

    return (
        {
            "index": index,
            "file": name,
            "progress": round(progress, 3),
            "brightness": round(brightness, 2),
            "saturation": round(saturation, 2),
            "sharpness": round(sharpness, 2),
            "contrast": round(contrast, 2),
            "face_detected": bool(face.detected),
            "face_confidence": round(float(face.confidence), 3),
            "face_ratio": round(face_ratio, 4),
            "face_center": [round(float(center[0]), 3), round(float(center[1]), 3)],
            "shot_size": _shot_size(face_ratio),
            "composition": _composition(center),
            "visual_state": _visual_state(brightness, saturation, sharpness),
            "source_size": [int(w), int(h)],
        },
        small_gray,
    )


def _shot_size(face_ratio: float) -> str:
    if face_ratio >= 0.22:
        return "closeup"
    if face_ratio >= 0.1:
        return "medium_closeup"
    if face_ratio >= 0.04:
        return "half_body"
    return "wide_or_unclear"


def _composition(center: tuple[float, float]) -> str:
    x, y = center
    if abs(x - 0.5) <= 0.08 and 0.32 <= y <= 0.58:
        return "center_locked"
    if abs(x - 0.5) <= 0.16:
        return "near_center"
    return "off_center"


def _visual_state(brightness: float, saturation: float, sharpness: float) -> str:
    if saturation < 35 and brightness < 105:
        return "dark_low_saturation_atmosphere"
    if saturation < 45:
        return "monochrome_or_low_saturation"
    if sharpness < 80:
        return "soft_or_motion_blur"
    if brightness > 135 and sharpness > 120:
        return "clear_highlight"
    return "balanced_color"


def _frame_role(index: int, total: int, features: dict[str, Any]) -> str:
    progress = index / max(1, total - 1)
    if progress < 0.18:
        return "atmosphere_setup"
    if progress < 0.38:
        return "reveal_transition"
    if progress < 0.78:
        return "core_visual_hold"
    if features["sharpness"] > 120 or features["face_detected"]:
        return "memory_point"
    return "ending_hold"


def _frame_edit_hint(index: int, total: int, features: dict[str, Any]) -> dict[str, str]:
    progress = index / max(1, total - 1)
    if progress < 0.18:
        effect = "mono_mystery" if features["saturation"] < 55 else "soft_blur_reveal"
        transition = "hard_cut"
    elif progress < 0.38:
        effect = "clarity_rise"
        transition = "glow_flash" if features["brightness"] > 120 else "hard_cut"
    elif progress < 0.78:
        effect = "cool_white_face_glow" if features["face_detected"] else "breathing_zoom"
        transition = "hard_cut"
    else:
        effect = "beauty_freeze" if features["face_detected"] else "slight_zoom"
        transition = "flash_white" if index == total - 1 else "hard_cut"
    return {
        "preferred_effect": effect,
        "preferred_transition": transition,
        "duration_hint": "0.35-0.7s" if progress < 0.4 else "0.6-1.2s",
    }


def _build_relations(frames: list[dict[str, Any]]) -> list[dict[str, Any]]:
    relations = []
    for prev, current in zip(frames, frames[1:]):
        brightness_delta = round(current["brightness"] - prev["brightness"], 2)
        saturation_delta = round(current["saturation"] - prev["saturation"], 2)
        sharpness_delta = round(current["sharpness"] - prev["sharpness"], 2)
        face_delta = round(current["face_ratio"] - prev["face_ratio"], 4)
        center_delta = _center_delta(prev.get("face_center"), current.get("face_center"))
        jump_score = abs(brightness_delta) / 30 + abs(saturation_delta) / 35 + abs(face_delta) * 8 + center_delta * 4
        relation_type = "same_shot_micro_progression" if jump_score < 1.2 else "cut_or_visual_jump"
        if sharpness_delta > 60 and current["brightness"] >= prev["brightness"]:
            progression = "clarity_upgrade"
        elif saturation_delta > 20:
            progression = "color_reveal"
        elif center_delta < 0.06 and abs(face_delta) < 0.025:
            progression = "composition_hold"
        else:
            progression = "rhythm_variation"
        relations.append(
            {
                "from": prev["index"],
                "to": current["index"],
                "relation_type": relation_type,
                "progression": progression,
                "brightness_delta": brightness_delta,
                "saturation_delta": saturation_delta,
                "sharpness_delta": sharpness_delta,
                "face_ratio_delta": face_delta,
                "center_delta": round(center_delta, 4),
            }
        )
    return relations


def _center_delta(a: list[float] | None, b: list[float] | None) -> float:
    if not a or not b:
        return 0.0
    return float(((float(a[0]) - float(b[0])) ** 2 + (float(a[1]) - float(b[1])) ** 2) ** 0.5)


def _build_windows(frames: list[dict[str, Any]], sizes: list[int]) -> list[dict[str, Any]]:
    windows = []
    for size in sizes:
        if len(frames) < size:
            continue
        for start in range(0, len(frames) - size + 1):
            chunk = frames[start : start + size]
            windows.append(
                {
                    "range": [chunk[0]["index"], chunk[-1]["index"]],
                    "size": size,
                    "section_role": _section_role(chunk),
                    "trend": _trend(chunk),
                    "dominant_shot": _dominant_value(chunk, "shot_size"),
                    "dominant_composition": _dominant_value(chunk, "composition"),
                }
            )
    return windows


def _section_role(chunk: list[dict[str, Any]]) -> str:
    avg_progress = sum(item["progress"] for item in chunk) / len(chunk)
    if avg_progress < 0.25:
        return "opening_reveal_unit"
    if avg_progress < 0.55:
        return "transition_to_core_unit"
    if avg_progress < 0.82:
        return "core_hold_unit"
    return "ending_memory_unit"


def _trend(chunk: list[dict[str, Any]]) -> str:
    first = chunk[0]
    last = chunk[-1]
    if last["sharpness"] - first["sharpness"] > 50:
        return "becomes_clearer"
    if last["saturation"] - first["saturation"] > 25:
        return "becomes_more_colorful"
    if last["brightness"] - first["brightness"] > 20:
        return "becomes_brighter"
    if all(item["composition"] in {"center_locked", "near_center"} for item in chunk):
        return "stable_center_hold"
    return "mixed_micro_changes"


def _dominant_value(items: list[dict[str, Any]], key: str) -> str:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(key, "unknown"))
        counts[value] = counts.get(value, 0) + 1
    return max(counts.items(), key=lambda pair: pair[1])[0]


def _distill_skill(
    frames: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    windows: list[dict[str, Any]],
) -> dict[str, Any]:
    closeup_share = _share(frames, lambda item: item["shot_size"] in {"closeup", "medium_closeup"})
    center_share = _share(frames, lambda item: item["composition"] in {"center_locked", "near_center"})
    low_sat_opening = any(item["saturation"] < 55 for item in frames[: max(1, len(frames) // 4)])
    micro_relation_share = _share(relations, lambda item: item["relation_type"] == "same_shot_micro_progression")
    reveal_trends = [item["trend"] for item in windows if item["section_role"] in {"opening_reveal_unit", "transition_to_core_unit"}]
    return {
        "id": "frame_to_edit_person_visual_reveal",
        "name": "Frame-to-edit 人物视觉递进",
        "confidence": round((closeup_share * 0.35 + center_share * 0.3 + micro_relation_share * 0.25 + (0.1 if low_sat_opening else 0)), 3),
        "core_logic": [
            "先识别每帧的视觉状态，而不是套固定风格词。",
            "用前后帧关系判断是微递进、揭晓、跳切还是记忆点。",
            "把 5 帧和 8 帧窗口压缩成段落角色，再映射到 timeline 节奏。",
        ],
        "structure_rules": [
            "开头使用氛围或不完整信息建立期待。",
            "中段逐步提升清晰度、亮度、色彩或接近感。",
            "主体段保持人物/主体连续，避免无意义大跳变。",
            "结尾停在最完整、最清晰、最有记忆点的画面。",
        ],
        "frame_relation_rules": [
            "相邻帧只允许一个主要变量变化：清晰度、亮度、色彩、距离或构图。",
            "前 5 帧判断开场策略，前 8 帧判断视频是揭晓型、动作型还是稳定展示型。",
            "如果构图相近但清晰度/亮度上升，使用微推进和轻卡点；如果构图突变，使用硬切或短闪。",
        ],
        "detected_traits": {
            "closeup_share": round(closeup_share, 3),
            "center_or_near_center_share": round(center_share, 3),
            "same_shot_micro_progression_share": round(micro_relation_share, 3),
            "low_saturation_opening": low_sat_opening,
            "early_window_trends": sorted(set(reveal_trends)),
        },
        "effect_mapping": {
            "atmosphere_setup": ["mono_mystery", "soft_blur_reveal", "slow_zoom_in"],
            "reveal_transition": ["clarity_rise", "desaturate_to_color", "glow_flash"],
            "core_visual_hold": ["cool_white_face_glow", "breathing_zoom", "hair_rim_light"],
            "memory_point": ["beauty_freeze", "slight_zoom", "flash_white"],
        },
        "avoid_rules": [
            "不要把具体颜色、舞台、眼神写死成唯一风格。",
            "不要让复杂转场抢走主体。",
            "不要让相邻帧同时大幅改变构图、色彩、速度和清晰度。",
        ],
    }


def _share(items: list[dict[str, Any]], predicate) -> float:
    if not items:
        return 0.0
    return sum(1 for item in items if predicate(item)) / len(items)


def _ai_status(use_ai: bool, ai_analysis: dict[str, Any] | None = None) -> str:
    if not use_ai:
        return "local_vision_only"
    if not settings.openai_api_key:
        return "ai_requested_but_openai_api_key_missing"
    if ai_analysis and ai_analysis.get("error"):
        return "ai_failed_local_result_kept"
    if ai_analysis:
        return "ai_enriched"
    return "ai_ready_prompt_generated"


def _multimodal_prompt(skill: dict[str, Any]) -> str:
    return (
        "请分析这张抽帧拼图/连续抽帧图，目标不是描述画面，而是复刻其剪辑逻辑。"
        "请输出：1) 每帧视觉状态；2) 相邻帧关系；3) 前5帧/前8帧段落功能；"
        "4) 可执行 timeline 规则；5) 滤镜/运镜/转场规则；6) 避坑规则。"
        f"参考当前本地蒸馏 skill：{skill['id']}，但不要写死具体颜色、舞台或人物眼神。"
    )


def _run_multimodal_analysis(frame_dir: Path, frames: list[Path], skill: dict[str, Any]) -> dict[str, Any] | None:
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        image_paths = _ai_image_paths(frame_dir, frames)
        content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": (
                    "You are analyzing sampled frames from a reference short video. "
                    "Do not describe the celebrity or fixed colors as the core answer. "
                    "Extract reusable editing logic for recreating a similar cut. "
                    "Return strict JSON with keys: frame_states, frame_relations, window_logic, "
                    "timeline_rules, filter_rules, camera_rules, transition_rules, avoid_rules, "
                    "skill_patch. The skill_patch must be abstract and reusable."
                    f"\nLocal distilled baseline:\n{json.dumps(skill, ensure_ascii=False)}"
                ),
            }
        ]
        for image_path in image_paths:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": _data_uri(image_path),
                        "detail": "low",
                    },
                }
            )
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": content}],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        raw = response.choices[0].message.content or "{}"
        return json.loads(raw)
    except Exception as exc:
        return {"error": str(exc)}


def _ai_image_paths(frame_dir: Path, frames: list[Path]) -> list[Path]:
    contact_sheet = frame_dir / "contact_sheet.jpg"
    if contact_sheet.exists():
        return [contact_sheet]
    if len(frames) <= 4:
        return frames
    indexes = np.linspace(0, len(frames) - 1, 4).round().astype(int)
    return [frames[int(index)] for index in indexes]


def _data_uri(path: Path) -> str:
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"
