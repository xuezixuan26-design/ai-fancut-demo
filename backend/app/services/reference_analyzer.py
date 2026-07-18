from collections import Counter
from pathlib import Path
import cv2
import numpy as np

from app.services.template_profile_catalog import apply_template_profile

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
    cut_times: list[float] = []
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
        cut_times = [round((index + 1) * sample_step / fps, 2) for index, value in enumerate(diffs) if value > threshold]
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
    opening_pattern = _opening_pattern(cut_times, flash_times, dark_times, face_ratios)
    climax_pattern = _climax_pattern(cut_times, flash_times, duration)
    motion_profile = _motion_profile(avg_shot, diffs)
    caption_frequency = _caption_frequency(cut_density, flash_times, duration)
    effect_intensity = _effect_intensity(cut_density, flash_times, diffs, duration)

    style = {
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
        "cut_times": cut_times[:24],
        "opening_pattern": opening_pattern,
        "climax_pattern": climax_pattern,
        "motion_profile": motion_profile,
        "caption_frequency": caption_frequency,
        "effect_intensity": effect_intensity,
        "edit_profile": _edit_profile(cut_density, flash_white, closeup_ratio),
    }
    style["reference_understanding"] = _reference_understanding(
        style=style,
        duration=duration,
        cut_times=cut_times,
        flash_times=flash_times,
        dark_times=dark_times,
        diffs=diffs,
        face_ratios=face_ratios,
    )
    return style


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
            "opening_pattern": "flash_closeup_hook",
            "climax_pattern": "strong_beat_flash_zoom",
            "motion_profile": "punchy_push",
            "caption_frequency": "medium",
            "effect_intensity": "strong",
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
            "opening_pattern": "slow_closeup_hook",
            "climax_pattern": "beauty_flash_hold",
            "motion_profile": "slow_push",
            "caption_frequency": "low",
            "effect_intensity": "medium",
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
            "opening_pattern": "slow_reveal_hook",
            "climax_pattern": "soft_hold",
            "motion_profile": "slow_push",
            "caption_frequency": "low",
            "effect_intensity": "subtle",
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
            "opening_pattern": "soft_closeup_hook",
            "climax_pattern": "soft_hold",
            "motion_profile": "gentle_drift",
            "caption_frequency": "medium",
            "effect_intensity": "subtle",
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
            "opening_pattern": "beat_cut_hook",
            "climax_pattern": "strong_beat_flash_zoom",
            "motion_profile": "punchy_push",
            "caption_frequency": "low",
            "effect_intensity": "strong",
            "edit_profile": "stage_beat_cut",
        },
        "progressive_idol_beauty": {
            "avg_shot_duration": 0.75,
            "cut_density": "high",
            "closeup_ratio": 0.62,
            "dominant_shot": "medium_closeup",
            "dominant_position": "center",
            "layout_profile": "progressive_center_beauty_stage",
            "color_grade": "cool_white_soft",
            "transition_style": ["hard_cut", "flash_white", "flash_black", "motion_blur"],
            "motion_style": ["slow_zoom", "snap_zoom", "motion_blur"],
            "caption_style": "bold_white_black_outline",
            "recommended_duration": 15,
            "opening_pattern": "pose_build_hook",
            "climax_pattern": "contrast_stage_climax",
            "motion_profile": "punchy_push",
            "caption_frequency": "low",
            "effect_intensity": "strong",
            "edit_profile": "progressive_idol_beauty",
            "structure_template": [
                {"section": "identity_setup", "range": [0.0, 0.2], "goal": "用清晰轮廓和干净动作建立人物与氛围"},
                {"section": "action_accelerate", "range": [0.2, 0.38], "goal": "用动作幅度递增和鼓点切镜提升节奏"},
                {"section": "contrast_bridge", "range": [0.38, 0.45], "goal": "用极短模糊、闪切或色彩反差完成情绪升级"},
                {"section": "beauty_core", "range": [0.45, 0.68], "goal": "集中展示高价值脸部、半身和造型记忆点"},
                {"section": "performance_climax", "range": [0.68, 0.9], "goal": "回到动作和舞台表现，保持主角视觉中心"},
                {"section": "ending_memory", "range": [0.9, 1.0], "goal": "用最稳定的高价值画面慢放或定格收尾"}
            ],
            "shot_priority": [
                "high_value_face_or_upper_body",
                "clear_profile_or_front_half_body",
                "clean_action_peak",
                "styling_or_silhouette_motion",
                "centered_lead_in_group_or_stage"
            ],
        },
        "monochrome_beauty_reveal": {
            "avg_shot_duration": 1.25,
            "cut_density": "low",
            "closeup_ratio": 0.78,
            "dominant_shot": "closeup",
            "dominant_position": "center",
            "layout_profile": "center_face_micro_progression",
            "color_grade": "cool_white_face_glow",
            "transition_style": ["hard_cut", "crossfade", "glow_flash"],
            "motion_style": ["micro_push", "breathing_zoom"],
            "caption_style": "minimal_or_none",
            "recommended_duration": 12,
            "opening_pattern": "monochrome_mystery_reveal",
            "climax_pattern": "beauty_hold_memory",
            "motion_profile": "micro_push",
            "caption_frequency": "low",
            "effect_intensity": "subtle",
            "edit_profile": "monochrome_to_color_beauty",
            "structure_template": [
                {"section": "atmosphere_setup", "range": [0.0, 0.15], "goal": "偏暗、黑白或低饱和、轻模糊，人物居中但不急于完全展示"},
                {"section": "clarity_reveal", "range": [0.15, 0.35], "goal": "逐步提升亮度、清晰度、锐度和饱和度，让脸部自然显现"},
                {"section": "beauty_hold", "range": [0.35, 0.75], "goal": "高清彩色近景或特写，突出冷白肤色、眼部高光、唇部和发丝细节"},
                {"section": "memory_freeze", "range": [0.75, 1.0], "goal": "维持高颜值状态，用轻微定格、微推近或柔光收尾"}
            ],
            "frame_relation_rule": "同构图微递进，每一帧只增加一点亮度、清晰度、彩色度或接近感",
            "portrait_treatment": {
                "face": ["natural_skin_smooth", "face_brighten", "eye_sharpen", "preserve_facial_shadow"],
                "hair": ["edge_sharpen", "rim_highlight", "retain_dark_detail"],
                "background": ["soft_blur", "cool_tone", "lower_exposure", "do_not_compete_with_face"]
            },
        },
        "contrast_special": {
            "avg_shot_duration": 1.05,
            "cut_density": "high",
            "closeup_ratio": 0.58,
            "dominant_shot": "medium_closeup",
            "dominant_position": "center",
            "layout_profile": "two_source_contrast_reveal",
            "color_grade": "contrast_split_beauty",
            "transition_style": ["soft_wash", "zoom_burst", "spin_blur", "whip_flash", "glow_flash"],
            "motion_style": ["slow_zoom", "snap_zoom", "slow_motion"],
            "caption_style": "minimal_or_none",
            "recommended_duration": 18,
            "opening_pattern": "first_source_setup",
            "climax_pattern": "second_source_reveal",
            "motion_profile": "contrast_push_rebound",
            "caption_frequency": "low",
            "effect_intensity": "strong",
            "edit_profile": "contrast_two_video",
            "structure_template": [
                {"section": "setup_a", "range": [0.0, 0.34], "goal": "Use first source family as baseline/setup with steadier motion."},
                {"section": "contrast_bridge", "range": [0.34, 0.46], "goal": "Use zoom/spin/flash bridge to announce the contrast turn."},
                {"section": "reveal_b", "range": [0.46, 0.84], "goal": "Use second source family as stronger reveal/highlight."},
                {"section": "memory_lock", "range": [0.84, 1.0], "goal": "End on the strongest B-side face or upper-body highlight."},
            ],
            "source_policy": {
                "requires_source_families": 2,
                "family_a_range": [0.0, 0.42],
                "family_b_range": [0.42, 1.0],
                "max_family_share": 0.62,
            },
        },
    }
    return apply_template_profile(templates.get(name, templates["korean_cool_white"]) | {"template": name}, name)


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


def _opening_pattern(cut_times: list[float], flash_times: list[float], dark_times: list[float], face_ratios: list[float]) -> str:
    opening_cuts = sum(1 for time in cut_times if time <= 3.0)
    opening_flashes = sum(1 for time in flash_times if time <= 3.0)
    dark_reveal = any(time <= 1.5 for time in dark_times)
    early_closeup = any(ratio >= 0.08 for ratio in face_ratios[:6])
    if dark_reveal:
        return "slow_reveal_hook"
    if opening_flashes:
        return "flash_closeup_hook" if early_closeup else "beat_cut_hook"
    if opening_cuts >= 3:
        return "beat_cut_hook"
    if early_closeup:
        return "slow_closeup_hook"
    return "soft_closeup_hook"


def _climax_pattern(cut_times: list[float], flash_times: list[float], duration: float) -> str:
    if duration <= 0:
        return "beauty_flash_hold"
    start = duration * 0.48
    end = duration * 0.86
    climax_cuts = sum(1 for time in cut_times if start <= time <= end)
    climax_flashes = sum(1 for time in flash_times if start <= time <= end)
    density = climax_cuts / max(1.0, end - start)
    if climax_flashes >= 2 or density >= 1.2:
        return "strong_beat_flash_zoom"
    if climax_flashes:
        return "beauty_flash_hold"
    return "soft_hold"


def _motion_profile(avg_shot: float, diffs: list[float]) -> str:
    if not diffs:
        return "slow_push"
    avg_motion = float(np.mean(diffs))
    if avg_shot < 1.0 or avg_motion >= 24:
        return "punchy_push"
    if avg_motion >= 15:
        return "gentle_drift"
    return "slow_push"


def _caption_frequency(cut_density: str, flash_times: list[float], duration: float) -> str:
    flash_density = len(flash_times) / max(1.0, duration)
    if cut_density == "high" and flash_density >= 0.04:
        return "medium"
    if cut_density == "low":
        return "low"
    return "low"


def _effect_intensity(cut_density: str, flash_times: list[float], diffs: list[float], duration: float) -> str:
    flash_density = len(flash_times) / max(1.0, duration)
    motion = float(np.mean(diffs)) if diffs else 0.0
    if cut_density == "high" or flash_density >= 0.05 or motion >= 24:
        return "strong"
    if cut_density == "medium" or flash_density > 0 or motion >= 15:
        return "medium"
    return "subtle"


def _reference_understanding(
    style: dict,
    duration: float,
    cut_times: list[float],
    flash_times: list[float],
    dark_times: list[float],
    diffs: list[float],
    face_ratios: list[float],
) -> dict:
    rhythm_curve = _rhythm_curve(duration, cut_times, flash_times, diffs)
    turning_points = _turning_points(duration, cut_times, flash_times, dark_times)
    return {
        "schema": "ai-fancut.reference-understanding.v1",
        "structure": rhythm_curve,
        "rhythm_curve": rhythm_curve,
        "turning_point_hints": {
            "times": turning_points[:8],
            "opening_to_build": 0.18,
            "build_to_drop": 0.48,
            "drop_to_outro": 0.82,
            "slow_motion_after_turn": bool(turning_points) or style.get("climax_pattern") in {"beauty_flash_hold", "soft_hold"},
        },
        "shot_relation_rules": [
            "compare each shot with previous shot by energy, clarity, color, and subject distance",
            "opening should establish subject before high-impact effects",
            "build should increase rhythm or subject proximity gradually",
            "turning point should create either contrast, flash/blur bridge, or slow-motion hold",
            "drop should alternate impact movement with face or upper-body memory points",
            "ending should reduce motion and leave a stable final frame",
        ],
        "slow_motion_logic": {
            "allowed_after": ["strong beat", "emotional turn", "pose hold", "face or upper-body high-value frame"],
            "avoid": ["opening", "transition gap", "wide running movement"],
            "preferred_speed_ranges": ["0.5-0.7", "0.3-0.4"],
        },
        "planner_hints": {
            "reference_driven": True,
            "prefer_revision_loop": True,
            "target_closeup_ratio": round(sum(1 for ratio in face_ratios if ratio >= 0.08) / max(1, len(face_ratios)), 2),
            "critic_should_check": ["shot_relation", "drop_lift", "slow_motion", "effect_repetition", "source_repetition"],
        },
    }


def _rhythm_curve(duration: float, cut_times: list[float], flash_times: list[float], diffs: list[float]) -> list[dict]:
    sections = [
        ("opening", 0.0, 0.18),
        ("build", 0.18, 0.48),
        ("drop", 0.48, 0.82),
        ("outro", 0.82, 1.0),
    ]
    result = []
    for name, start_ratio, end_ratio in sections:
        start = duration * start_ratio
        end = duration * end_ratio
        section_cuts = [time for time in cut_times if start <= time < end]
        section_flashes = [time for time in flash_times if start <= time < end]
        cut_rate = len(section_cuts) / max(0.1, end - start)
        flash_rate = len(section_flashes) / max(0.1, end - start)
        energy = min(1.0, 0.25 + cut_rate * 0.22 + flash_rate * 0.35)
        if name == "drop":
            energy = max(energy, 0.72)
        result.append(
            {
                "section": name,
                "range": [round(start_ratio, 3), round(end_ratio, 3)],
                "time_range": [round(start, 2), round(end, 2)],
                "energy": round(energy, 2),
                "cut_count": len(section_cuts),
                "flash_count": len(section_flashes),
            }
        )
    return result


def _turning_points(duration: float, cut_times: list[float], flash_times: list[float], dark_times: list[float]) -> list[dict]:
    candidates = []
    for time in flash_times:
        candidates.append({"time": time, "type": "flash_or_impact"})
    for time in dark_times:
        candidates.append({"time": time, "type": "dark_reveal"})
    for ratio, label in [(0.18, "opening_to_build"), (0.48, "build_to_drop"), (0.82, "drop_to_outro")]:
        target = duration * ratio
        nearest = min(cut_times, key=lambda value: abs(value - target), default=target) if cut_times else target
        candidates.append({"time": round(nearest, 2), "type": label})
    return sorted(candidates, key=lambda item: float(item["time"]))
