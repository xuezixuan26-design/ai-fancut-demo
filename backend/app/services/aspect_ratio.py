from __future__ import annotations

from app.config import settings


SUPPORTED_ASPECT_RATIOS = {
    "9:16": {"width": 1080, "height": 1920, "label": "Vertical 9:16"},
    "16:9": {"width": 1920, "height": 1080, "label": "Landscape 16:9"},
    "4:3": {"width": 1440, "height": 1080, "label": "Classic 4:3"},
}


def normalize_aspect_ratio(value: str | None) -> str:
    if not value:
        return "9:16"
    cleaned = str(value).replace("：", ":").strip()
    return cleaned if cleaned in SUPPORTED_ASPECT_RATIOS else "9:16"


def output_size(aspect_ratio: str | None) -> tuple[int, int]:
    normalized = normalize_aspect_ratio(aspect_ratio)
    spec = SUPPORTED_ASPECT_RATIOS.get(normalized)
    if spec:
        return int(spec["width"]), int(spec["height"])
    return int(settings.output_width), int(settings.output_height)
