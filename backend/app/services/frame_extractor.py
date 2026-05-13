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
        face = analyzer.detect_face(frame)
        sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        brightness = float(gray.mean())
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
        score = highlight_score(
            face_ratio_score,
            sharpness_score,
            center_score,
            brightness_score,
            stability_score,
        )
        reason_bits = []
        if face.detected:
            reason_bits.append("人脸清晰" if sharpness_score >= 6 else "检测到人脸")
            reason_bits.append("近景" if face.ratio >= 0.15 else "脸部偏小")
            reason_bits.append("构图居中" if center_score >= 7 else "构图可用")
        else:
            reason_bits.append("未检测到稳定人脸")

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
                "stability_score": round(stability_score, 2),
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
