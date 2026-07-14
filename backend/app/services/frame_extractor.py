from pathlib import Path
import cv2
import numpy as np

from app.services.face_analyzer import (
    FaceAnalyzer,
    highlight_score,
    normalize_brightness,
    normalize_center,
    normalize_face_ratio,
    normalize_sharpness,
    normalize_stability,
)


def analyze_video_frames(video_path: Path, interval_sec: float = 0.5) -> list[dict]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = total_frames / fps if fps else 0
    analyzer = FaceAnalyzer()
    rows: list[dict] = []
    prev_gray = None
    t = 0.0

    while t < duration:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if not ok:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        face = analyzer.detect_face(frame)
        sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        brightness = float(gray.mean())
        saturation = float(hsv[:, :, 1].mean())
        frame_diff = None
        if prev_gray is not None:
            small = cv2.resize(gray, (96, 54))
            prev_small = cv2.resize(prev_gray, (96, 54))
            frame_diff = float(np.mean(cv2.absdiff(small, prev_small)))
        prev_gray = gray

        face_ratio_score = normalize_face_ratio(face.ratio)
        sharpness_score = normalize_sharpness(sharpness)
        center_score = normalize_center(face.center)
        brightness_score = normalize_brightness(brightness)
        stability_score = normalize_stability(frame_diff)
        stage_lighting_score = _stage_lighting_score(brightness, saturation)
        motion_energy = _motion_energy(frame_diff)
        score = highlight_score(
            face_ratio_score,
            sharpness_score,
            center_score,
            brightness_score,
            stability_score,
        )
        shot_size = _shot_size(face.ratio, face.detected)
        subject_position = _subject_position(face.center)
        visual_tags = _visual_tags(face.detected, shot_size, subject_position, brightness, saturation, motion_energy)
        reason_bits = _reason_bits(face.detected, sharpness_score, face.ratio, center_score, visual_tags)

        rows.append(
            {
                "video": video_path.name,
                "timestamp": round(t, 2),
                "face_detected": face.detected,
                "face_confidence": round(face.confidence, 3),
                "face_bbox": face.bbox,
                "face_center": face.center,
                "face_ratio": round(face.ratio, 4),
                "face_ratio_score": round(face_ratio_score, 2),
                "sharpness": round(sharpness, 2),
                "sharpness_score": round(sharpness_score, 2),
                "center_score": round(center_score, 2),
                "brightness": round(brightness, 2),
                "brightness_score": round(brightness_score, 2),
                "saturation": round(saturation, 2),
                "stability_score": round(stability_score, 2),
                "motion_energy": motion_energy,
                "stage_lighting_score": round(stage_lighting_score, 2),
                "flash_like": brightness >= 220,
                "shot_size": shot_size,
                "subject_position": subject_position,
                "visual_tags": visual_tags,
                "scene_role": _scene_role(score, shot_size, motion_energy, brightness),
                "highlight_score": score,
                "reason": "，".join(reason_bits),
            }
        )
        t += interval_sec

    cap.release()
    return rows


def analyze_materials(video_paths: list[Path], interval_sec: float = 0.5) -> list[dict]:
    rows: list[dict] = []
    for path in video_paths:
        rows.extend(analyze_video_frames(path, interval_sec))
    return rows


def _shot_size(face_ratio: float, detected: bool) -> str:
    if not detected:
        return "unknown"
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


def _motion_energy(frame_diff: float | None) -> str:
    if frame_diff is None:
        return "unknown"
    if frame_diff >= 26:
        return "high"
    if frame_diff >= 12:
        return "medium"
    return "low"


def _stage_lighting_score(brightness: float, saturation: float) -> float:
    bright_pop = np.clip((brightness - 120) / 80 * 5, 0, 5)
    color_pop = np.clip((saturation - 55) / 90 * 5, 0, 5)
    return float(bright_pop + color_pop)


def _visual_tags(
    face_detected: bool,
    shot_size: str,
    subject_position: str,
    brightness: float,
    saturation: float,
    motion_energy: str,
) -> list[str]:
    tags = []
    if face_detected:
        tags.append("face_visible")
    if shot_size in {"closeup", "medium_closeup"}:
        tags.append("beauty_focus")
    if subject_position in {"center", "upper_center"}:
        tags.append("center_composition")
    if brightness >= 220:
        tags.append("flash_or_white_frame")
    if brightness <= 45:
        tags.append("black_or_dark_frame")
    if saturation >= 105:
        tags.append("stage_color_pop")
    if motion_energy == "high":
        tags.append("high_motion")
    return tags


def _scene_role(score: float, shot_size: str, motion_energy: str, brightness: float) -> str:
    if brightness >= 220:
        return "transition_flash"
    if score >= 8 and shot_size in {"closeup", "medium_closeup"}:
        return "hook_or_climax"
    if motion_energy == "high":
        return "beat_cut"
    if shot_size in {"closeup", "medium_closeup"}:
        return "beauty_hold"
    return "supporting"


def _reason_bits(
    face_detected: bool,
    sharpness_score: float,
    face_ratio: float,
    center_score: float,
    visual_tags: list[str],
) -> list[str]:
    if not face_detected:
        return ["未检测到稳定人脸", "按清晰度/亮度兜底"]
    bits = ["人脸清晰" if sharpness_score >= 6 else "检测到人脸"]
    bits.append("近景/特写" if face_ratio >= 0.08 else "人物偏远")
    bits.append("构图居中" if center_score >= 7 else "构图可用")
    if "stage_color_pop" in visual_tags:
        bits.append("舞台色彩明显")
    if "high_motion" in visual_tags:
        bits.append("运动变化强")
    return bits
