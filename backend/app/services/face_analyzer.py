from dataclasses import dataclass
import cv2
import numpy as np


@dataclass
class FaceResult:
    detected: bool
    confidence: float = 0.0
    bbox: tuple[int, int, int, int] | None = None
    center: tuple[float, float] | None = None
    ratio: float = 0.0


class FaceAnalyzer:
    def __init__(self) -> None:
        self.detector = None
        try:
            import mediapipe as mp

            self.detector = mp.solutions.face_detection.FaceDetection(
                model_selection=1,
                min_detection_confidence=0.45,
            )
        except Exception:
            self.detector = None

    def detect_face(self, frame_bgr: np.ndarray) -> FaceResult:
        h, w = frame_bgr.shape[:2]
        if self.detector is None:
            return self._detect_face_haar(frame_bgr)

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        result = self.detector.process(rgb)
        detections = result.detections or []
        if not detections:
            return FaceResult(False)

        best = max(detections, key=lambda d: d.score[0] if d.score else 0)
        box = best.location_data.relative_bounding_box
        x = max(0, int(box.xmin * w))
        y = max(0, int(box.ymin * h))
        bw = min(w - x, int(box.width * w))
        bh = min(h - y, int(box.height * h))
        ratio = (bw * bh) / float(w * h)
        center = ((x + bw / 2) / w, (y + bh / 2) / h)
        return FaceResult(True, float(best.score[0]), (x, y, bw, bh), center, ratio)

    def _detect_face_haar(self, frame_bgr: np.ndarray) -> FaceResult:
        h, w = frame_bgr.shape[:2]
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(48, 48))
        if len(faces) == 0:
            return FaceResult(False)
        x, y, bw, bh = max(faces, key=lambda b: b[2] * b[3])
        ratio = (bw * bh) / float(w * h)
        return FaceResult(True, 0.65, (int(x), int(y), int(bw), int(bh)), ((x + bw / 2) / w, (y + bh / 2) / h), ratio)


def normalize_face_ratio(face_ratio: float) -> float:
    if face_ratio <= 0:
        return 0.0
    if 0.15 <= face_ratio <= 0.35:
        return 10.0
    if face_ratio < 0.15:
        return max(0.0, face_ratio / 0.15 * 10.0)
    return max(0.0, 10.0 - (face_ratio - 0.35) / 0.35 * 10.0)


def normalize_sharpness(laplacian_var: float) -> float:
    return float(np.clip((laplacian_var - 40.0) / 180.0 * 10.0, 0.0, 10.0))


def normalize_center(center: tuple[float, float] | None) -> float:
    if center is None:
        return 0.0
    dx = abs(center[0] - 0.5)
    dy = abs(center[1] - 0.48)
    dist = (dx * dx + dy * dy) ** 0.5
    return float(np.clip(10.0 - dist / 0.5 * 10.0, 0.0, 10.0))


def normalize_brightness(mean_luma: float) -> float:
    if 80 <= mean_luma <= 190:
        return 10.0
    if mean_luma < 80:
        return float(np.clip(mean_luma / 80.0 * 10.0, 0.0, 10.0))
    return float(np.clip((255.0 - mean_luma) / 65.0 * 10.0, 0.0, 10.0))


def normalize_stability(frame_diff: float | None) -> float:
    if frame_diff is None:
        return 7.0
    return float(np.clip(10.0 - frame_diff / 35.0 * 10.0, 0.0, 10.0))


def highlight_score(
    face_ratio_score: float,
    sharpness_score: float,
    center_score: float,
    brightness_score: float,
    stability_score: float,
) -> float:
    return round(
        0.30 * face_ratio_score
        + 0.25 * sharpness_score
        + 0.20 * center_score
        + 0.15 * brightness_score
        + 0.10 * stability_score,
        2,
    )
