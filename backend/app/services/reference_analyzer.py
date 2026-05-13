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
    analyzer = FaceAnalyzer()

    index = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if index % sample_step == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            brightness_values.append(float(gray.mean()))
            sat_values.append(float(hsv[:, :, 1].mean()))
            face = analyzer.detect_face(frame)
            if face.detected:
                face_ratios.append(face.ratio)
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
    flash_white = any(b > 210 for b in brightness_values)
    avg_sat = sum(sat_values) / len(sat_values) if sat_values else 90
    avg_brightness = sum(brightness_values) / len(brightness_values) if brightness_values else 128
    closeup_ratio = sum(1 for r in face_ratios if r >= 0.12) / max(1, len(face_ratios))
    cut_density = "high" if avg_shot < 1.5 else "medium" if avg_shot < 2.8 else "low"
    color_grade = "cool_white_soft" if avg_brightness >= 135 and avg_sat < 95 else "cinematic_low_saturation" if avg_sat < 75 else "warm_soft"

    return {
        "avg_shot_duration": round(avg_shot, 2),
        "cut_density": cut_density,
        "closeup_ratio": round(closeup_ratio, 2),
        "color_grade": color_grade,
        "transition_style": ["hard_cut", "flash_white"] if flash_white else ["hard_cut"],
        "motion_style": ["slow_zoom", "slow_motion"] if avg_shot > 1.0 else ["slight_zoom"],
        "caption_style": "bold_white_black_outline",
        "recommended_duration": 30 if duration >= 30 else max(20, round(duration)),
        "duration": round(duration, 2),
        "estimated_cuts": cut_count,
    }


def default_style_template(name: str = "korean_cool_white") -> dict:
    templates = {
        "divine_beat": {
            "avg_shot_duration": 1.0,
            "cut_density": "high",
            "color_grade": "cool_white_soft",
            "transition_style": ["hard_cut", "flash_white"],
            "motion_style": ["slow_zoom", "slow_motion"],
            "caption_style": "bold_white_black_outline",
            "recommended_duration": 30,
        },
        "korean_cool_white": {
            "avg_shot_duration": 1.2,
            "cut_density": "medium",
            "color_grade": "cool_white_soft",
            "transition_style": ["hard_cut", "flash_white"],
            "motion_style": ["slow_zoom"],
            "caption_style": "bold_white_black_outline",
            "recommended_duration": 30,
        },
        "cinematic": {
            "avg_shot_duration": 1.8,
            "cut_density": "low",
            "color_grade": "cinematic_low_saturation",
            "transition_style": ["hard_cut", "crossfade"],
            "motion_style": ["slow_zoom"],
            "caption_style": "bold_white_black_outline",
            "recommended_duration": 35,
        },
        "sweet": {
            "avg_shot_duration": 1.4,
            "cut_density": "medium",
            "color_grade": "warm_soft",
            "transition_style": ["hard_cut"],
            "motion_style": ["slight_zoom"],
            "caption_style": "bold_white_black_outline",
            "recommended_duration": 30,
        },
        "stage": {
            "avg_shot_duration": 0.8,
            "cut_density": "high",
            "color_grade": "cool_white_soft",
            "transition_style": ["hard_cut", "flash_white"],
            "motion_style": ["slight_zoom"],
            "caption_style": "bold_white_black_outline",
            "recommended_duration": 25,
        },
    }
    return templates.get(name, templates["korean_cool_white"]) | {"template": name}
