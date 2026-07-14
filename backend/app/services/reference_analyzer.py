from collections import Counter
from pathlib import Path
import cv2
import numpy as np

from app.services.face_analyzer import FaceAnalyzer


def analyze_reference_video(path: Path) -> dict:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open reference video: {path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = total / fps if fps else 0
    sample_step = max(1, int(fps * 0.5))
    prev_gray = None
    diffs: list[float] = []
    brightness_values: list[float] = []
    sat_values: list[float] = []
    face_ratios: list[float] = []
    shot_sizes: list[str] = []
    positions: list[str] = []
    flash_times: list[float] = []
    dark_times: list[float] = []
    analyzer = FaceAnalyzer()

    index = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if index % sample_step == 0:
            time_sec = index / fps if fps else 0
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            brightness = float(gray.mean())
            saturation = float(hsv[:, :, 1].mean())
            brightness_values.append(brightness)
            sat_values.append(saturation)
            if brightness > 220:
                flash_times.append(round(time_sec, 2))
            if brightness < 42:
                dark_times.append(round(time_sec, 2))
            face = analyzer.detect_face(frame)
            if face.detected:
                face_ratios.append(face.ratio)
                shot_sizes.append(_shot_size(face.ratio))
                positions.append(_subject_position(face.center))
            if prev_gray is not None:
                diffs.append(float(np.mean(cv2.absdiff(cv2.resize(gray, (96, 54)), cv2.resize(prev_gray, (96, 54))))))
            prev_gray = gray
        index += 1
    cap.release()

    if diffs:
        threshold = float(np.mean(diffs) + np.std(diffs) * 1.2)
        cuts = [d for d in diffs if d > threshold]
    else:
        cuts = []
    cut_count = len(cuts)
    avg_shot = duration / max(1, cut_count + 1)
    flash_white = len(flash_times) > 0
    avg_sat = sum(sat_values) / len(sat_values) if sat_values else 90
    avg_brightness = sum(brightness_values) / len(brightness_values) if brightness_values else 128
    closeup_ratio = sum(1 for r in face_ratios if r >= 0.12) / max(1, len(face_ratios))
    cut_density = "high" if avg_shot < 1.5 else "medium" if avg_shot < 2.8 else "low"
    color_grade = "cool_white_soft" if avg_brightness >= 135 and avg_sat < 95 else "cinematic_low_saturation" if avg_sat < 75 else "warm_soft"
    dominant_shot = _majority(shot_sizes, "medium_closeup")
    dominant_position = _majority(positions, "center")

    return {
        "avg_shot_duration": round(avg_shot, 2),
        "cut_density": cut_density,
        "closeup_ratio": round(closeup_ratio, 2),
        "dominant_shot": dominant_shot,
        "dominant_position": dominant_position,
        "layout_profile": _layout_profile(dominant_shot, dominant_position, closeup_ratio),
        "color_grade": color_grade,
        "transition_style": ["hard_cut", "flash_white"] if flash_white else ["hard_cut"],
        "motion_style": ["slow_zoom", "slow_motion"] if avg_shot > 1.0 else ["slight_zoom"],
        "caption_style": "bold_white_black_outline",
        "recommended_duration": 30 if duration >= 30 else max(20, round(duration)),
        "duration": round(duration, 2),
        "estimated_cuts": cut_count,
        "flash_density": round(len(flash_times) / max(1, duration), 3),
        "flash_times": flash_times[:12],
        "dark_reveal_times": dark_times[:8],
        "edit_profile": _edit_profile(cut_density, flash_white, closeup_ratio),
    }


def default_style_template(name: str = "korean_cool_white") -> dict:
    templates = {
        "divine_beat": {
            "avg_shot_duration": 1.0,
            "cut_density": "high",
            "closeup_ratio": 0.7,
            "dominant_shot": "closeup",
            "dominant_position": "center",
            "layout_profile": "center_closeup_hook",
            "color_grade": "cool_white_soft",
            "transition_style": ["hard_cut", "flash_white"],
            "motion_style": ["slow_zoom", "slow_motion"],
            "caption_style": "bold_white_black_outline",
            "recommended_duration": 30,
            "edit_profile": "beat_flash_beauty",
        },
        "korean_cool_white": {
            "avg_shot_duration": 1.2,
            "cut_density": "medium",
            "closeup_ratio": 0.6,
            "dominant_shot": "medium_closeup",
            "dominant_position": "center",
            "layout_profile": "clean_center_beauty",
            "color_grade": "cool_white_soft",
            "transition_style": ["hard_cut", "flash_white"],
            "motion_style": ["slow_zoom"],
            "caption_style": "bold_white_black_outline",
            "recommended_duration": 30,
            "edit_profile": "cool_white_beauty_hold",
        },
        "cinematic": {
            "avg_shot_duration": 1.8,
            "cut_density": "low",
            "closeup_ratio": 0.45,
            "dominant_shot": "medium_closeup",
            "dominant_position": "center",
            "layout_profile": "slow_atmosphere_portrait",
            "color_grade": "cinematic_low_saturation",
            "transition_style": ["hard_cut", "crossfade"],
            "motion_style": ["slow_zoom"],
            "caption_style": "bold_white_black_outline",
            "recommended_duration": 35,
            "edit_profile": "slow_mood_beauty",
        },
        "sweet": {
            "avg_shot_duration": 1.4,
            "cut_density": "medium",
            "closeup_ratio": 0.55,
            "dominant_shot": "medium_closeup",
            "dominant_position": "center",
            "layout_profile": "soft_center_beauty",
            "color_grade": "warm_soft",
            "transition_style": ["hard_cut"],
            "motion_style": ["slight_zoom"],
            "caption_style": "bold_white_black_outline",
            "recommended_duration": 30,
            "edit_profile": "sweet_intro_hold",
        },
        "stage": {
            "avg_shot_duration": 0.8,
            "cut_density": "high",
            "closeup_ratio": 0.45,
            "dominant_shot": "half_body",
            "dominant_position": "center",
            "layout_profile": "stage_center_motion",
            "color_grade": "cool_white_soft",
            "transition_style": ["hard_cut", "flash_white"],
            "motion_style": ["slight_zoom"],
            "caption_style": "bold_white_black_outline",
            "recommended_duration": 25,
            "edit_profile": "stage_beat_cut",
        },
    }
    return templates.get(name, templates["korean_cool_white"]) | {"template": name}


def _shot_size(face_ratio: float) -> str:
    if face_ratio >= 0.18:
        return "closeup"
    if face_ratio >= 0.08:
        return "medium_closeup"
    if face_ratio >= 0.035:
        return "half_body"
    return "full_body"


def _subject_position(center: tuple[float, float] | None) -> str:
    if center is None:
        return "unknown"
    x, y = center
    if y < 0.35:
        vertical = "upper"
    elif y > 0.68:
        vertical = "lower"
    else:
        vertical = ""
    if x < 0.38:
        horizontal = "left"
    elif x > 0.62:
        horizontal = "right"
    else:
        horizontal = "center"
    return f"{vertical}_{horizontal}".strip("_")


def _majority(values: list[str], fallback: str) -> str:
    if not values:
        return fallback
    return Counter(values).most_common(1)[0][0]


def _layout_profile(dominant_shot: str, dominant_position: str, closeup_ratio: float) -> str:
    if closeup_ratio >= 0.65:
        return "center_closeup_hook"
    if dominant_shot in {"half_body", "full_body"}:
        return "stage_body_motion"
    if dominant_position != "center":
        return "off_center_portrait"
    return "clean_center_beauty"


def _edit_profile(cut_density: str, flash_white: bool, closeup_ratio: float) -> str:
    if cut_density == "high" and flash_white:
        return "beat_flash_beauty"
    if cut_density == "high":
        return "stage_beat_cut"
    if closeup_ratio >= 0.6:
        return "cool_white_beauty_hold"
    return "slow_mood_beauty"
