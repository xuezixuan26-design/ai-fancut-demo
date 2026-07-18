from __future__ import annotations

from copy import deepcopy
from typing import Any


TEMPLATE_PROFILES: dict[str, dict[str, Any]] = {
    "divine_beat": {
        "template_id": "divine_beat",
        "template_name": "神颜卡点风",
        "positioning": "爱豆特写颜值快剪、鼓点卡点短视频",
        "camera": {
            "mode": "快速推拉+微环绕",
            "shot_duration_range": [0.3, 0.8],
            "strength": 8,
            "motion_blur": True,
            "subject_lock": "face_mask",
            "keyframes": [{"t": 0.0, "scale": 1.0}, {"t": 0.5, "scale": 1.2}, {"t": 1.0, "scale": 1.08}],
        },
        "transition": {
            "type": "运镜转场-急速推拉闪切",
            "duration_range": [0.16, 0.24],
            "strength": 9,
            "light_overlay": True,
            "preferred": ["flash_white", "whip_flash", "zoom_burst", "shake_zoom"],
        },
        "render": {
            "filter": "冰肌冷调",
            "strength": 60,
            "brightness": 15,
            "contrast": 25,
            "sharpen": 50,
            "temperature": -8,
            "skin_smooth": 30,
            "particle": "星光闪粉",
            "particle_opacity": 25,
        },
        "constraints": ["no_face_occlusion", "closeup_first", "beat_peak_zoom_rebound"],
        "material_fit": ["怼脸直拍", "自拍特写", "五官局部镜头"],
    },
    "korean_cool_white": {
        "template_id": "korean_cool_white",
        "template_name": "韩系冷白风",
        "positioning": "清冷韩系爱豆、私服氛围感、慢节奏抒情饭制",
        "camera": {
            "mode": "缓慢推进+平稳横移",
            "shot_duration_range": [1.5, 4.0],
            "strength": 3,
            "motion_blur": False,
            "micro_shake": "low",
            "keyframes": [{"t": 0.0, "scale": 1.0}, {"t": 1.0, "scale": 1.12}],
        },
        "transition": {
            "type": "基础转场-柔化叠化",
            "duration_range": [0.8, 1.2],
            "strength": 4,
            "light_overlay": False,
            "preferred": ["crossfade", "soft_wash", "luma_fade"],
            "avoid": ["shake_zoom", "spin_blur", "whip_pan", "strobe_white"],
        },
        "render": {
            "filter": "冷白电影",
            "strength": 70,
            "temperature": -20,
            "saturation": -10,
            "highlight": -60,
            "orange_luminance": 20,
            "hair_rim_light_opacity": 30,
            "background_blur": "light",
            "fog_opacity": 15,
            "vignette": 20,
        },
        "constraints": ["stable_face_focus", "no_glitch_transition", "no_large_flash"],
        "material_fit": ["机场私服", "外景街拍", "清冷氛围感静态照", "慢动作"],
    },
    "cinematic": {
        "template_id": "cinematic",
        "template_name": "氛围电影风",
        "positioning": "长镜头叙事、故事感混剪、高级氛围感大片",
        "camera": {
            "mode": "长镜头环绕+升降慢拉",
            "shot_duration_range": [3.0, 6.0],
            "strength": 4,
            "film_shake": True,
            "keyframes": [{"t": 0.0, "x": -0.12, "y": 0.06, "scale": 1.1}, {"t": 1.0, "x": 0.12, "y": -0.08, "scale": 1.0}],
        },
        "transition": {
            "type": "蒙版遮罩转场+运镜衔接推拉",
            "duration_range": [0.8, 1.1],
            "strength": 5,
            "mask_feather": 60,
            "preferred": ["crossfade", "luma_fade", "soft_wash"],
        },
        "render": {
            "filter": "低饱和电影灰调",
            "strength": 50,
            "contrast": 10,
            "shadow": 30,
            "vignette": 40,
            "film_grain": 12,
            "edge_light": "tindall_side_beam",
        },
        "constraints": ["weaken_high_saturation", "prefer_environment_context", "long_take_first"],
        "material_fit": ["外景旅拍", "黄昏夜景", "连贯剧情向饭拍", "远景全景"],
    },
    "sweet": {
        "template_id": "sweet",
        "template_name": "甜向安利风",
        "positioning": "甜妹/温柔爱豆、治愈日常、安利向温柔短视频",
        "camera": {
            "mode": "轻柔小幅放大+上下微升降",
            "shot_duration_range": [1.0, 3.0],
            "strength": 2,
            "breathing": True,
            "keyframes": [{"t": 0.0, "y": 0.04, "scale": 1.0}, {"t": 1.0, "y": -0.04, "scale": 1.08}],
        },
        "transition": {
            "type": "基础转场-淡入淡出+柔光渐变擦除",
            "duration_range": [0.6, 0.8],
            "strength": 3,
            "preferred": ["crossfade", "soft_wash", "luma_fade"],
        },
        "render": {
            "filter": "蜜桃清透",
            "strength": 65,
            "temperature": 12,
            "red_saturation": 15,
            "skin_luminance": 22,
            "particle": "粉色爱心飘落",
            "particle_opacity": 30,
            "soft_light": "low",
        },
        "constraints": ["no_harsh_flash", "small_motion_only", "smile_or_cute_action_first"],
        "material_fit": ["笑容特写", "可爱小动作", "室内自拍", "甜系舞台慢放"],
    },
    "stage": {
        "template_id": "stage",
        "template_name": "高能舞台风",
        "positioning": "唱跳打歌、舞蹈卡点、炸场舞台快剪",
        "camera": {
            "mode": "急速推拉+跟镜+甩镜",
            "shot_duration_range": [0.2, 0.6],
            "strength": 10,
            "motion_blur": True,
            "keyframes": [{"t": 0.0, "x": -0.08, "scale": 1.0}, {"t": 0.45, "x": 0.08, "scale": 1.28}, {"t": 1.0, "x": 0.0, "scale": 1.12}],
        },
        "transition": {
            "type": "运镜甩动转场+闪白爆光",
            "duration_range": [0.12, 0.18],
            "strength": 10,
            "light_overlay": True,
            "rgb_shift": True,
            "preferred": ["whip_pan", "flash_white", "strobe_white", "shake_zoom", "zoom_burst"],
        },
        "render": {
            "filter": "Kpop霓虹舞台",
            "strength": 75,
            "saturation": 35,
            "blue_purple_shadow": "lift",
            "highlight": -70,
            "neon_body_rim": True,
            "particle": "金箔亮片",
        },
        "constraints": ["beat_locked_cut", "high_motion_ok", "short_flash_only"],
        "material_fit": ["打歌舞台", "直拍舞蹈", "团体刀群舞", "爆发力动作镜头"],
    },
    "progressive_idol_beauty": {
        "template_id": "progressive_idol_beauty",
        "template_name": "递进颜值复刻",
        "positioning": "不同时期物料对比、颜值成长向、渐变对比混剪",
        "camera": {
            "mode": "固定定点放大，统一缩放逻辑",
            "shot_duration_range": [1.6, 2.2],
            "strength": 1,
            "motion_blur": False,
            "keyframes": [{"t": 0.0, "scale": 1.0}, {"t": 1.0, "scale": 1.14}],
        },
        "transition": {
            "type": "分屏分割转场+渐变叠化",
            "duration_range": [0.8, 1.0],
            "strength": 4,
            "split_screen": "left_right",
            "preferred": ["crossfade", "luma_fade", "soft_wash"],
        },
        "render": {
            "filter": "统一冷白基底",
            "strength": 50,
            "skin_hsl_unify": True,
            "material_color_match": True,
            "particle": "轻微星光",
        },
        "constraints": ["uniform_camera_logic", "skin_color_consistency", "avoid_large_position_jump"],
        "material_fit": ["早年旧图vs近期高清物料", "不同年份舞台对比", "成长向合集"],
    },
    "monochrome_beauty_reveal": {
        "template_id": "monochrome_beauty_reveal",
        "template_name": "黑白揭晓颜值",
        "positioning": "悬疑氛围感、反差颜值向、黑白转彩色惊艳镜头",
        "camera": {
            "mode": "匀速缓慢推进人脸",
            "shot_duration_range": [2.0, 4.0],
            "strength": 3,
            "motion_blur": False,
            "keyframes": [{"t": 0.0, "scale": 1.0}, {"t": 1.0, "scale": 1.12}],
        },
        "transition": {
            "type": "黑白渐变上色转场+叠化",
            "duration_range": [0.9, 1.1],
            "strength": 5,
            "preferred": ["crossfade", "luma_fade", "glow_flash"],
        },
        "render": {
            "opening_filter": "黑白去色",
            "opening_contrast": 30,
            "opening_vignette": 35,
            "reveal_saturation_keyframe": [0, 100],
            "reveal_rim_light": True,
            "sharpen": 45,
            "reveal_particle": "星光闪光",
        },
        "constraints": ["monochrome_to_color_progression", "stable_face_center", "particle_only_on_reveal"],
        "material_fit": ["氛围感侧脸", "神秘远景", "反转惊艳怼脸镜头"],
    },
    "contrast_special": {
        "template_id": "contrast_special",
        "template_name": "Contrast Special",
        "positioning": "Two uploaded videos are edited as setup versus reveal, using source-family alternation and a clear contrast bridge.",
        "camera": {
            "mode": "slow setup push + zoom rebound reveal",
            "shot_duration_range": [0.7, 1.5],
            "strength": 6,
            "motion_blur": True,
            "keyframes": [{"t": 0.0, "scale": 1.0}, {"t": 0.55, "scale": 1.18}, {"t": 1.0, "scale": 1.08}],
        },
        "transition": {
            "type": "motion-linked zoom/spin contrast bridge",
            "duration_range": [0.45, 0.75],
            "strength": 7,
            "light_overlay": True,
            "preferred": ["soft_wash", "zoom_burst", "spin_blur", "whip_flash", "glow_flash"],
        },
        "render": {
            "filter": "contrast split beauty",
            "strength": 68,
            "setup_saturation": -12,
            "reveal_contrast": 22,
            "reveal_sharpen": 42,
            "bridge_flash": True,
        },
        "constraints": ["must_use_two_source_families", "first_family_setup", "second_family_reveal", "contrast_bridge_required", "avoid_single_family_dominance"],
        "material_fit": ["two contrasting uploads", "before-after idol edit", "soft-to-impact reveal", "daily-to-stage contrast"],
    },
}


ALIASES = {
    "beat_flash_beauty": "divine_beat",
    "cool_white_beauty_hold": "korean_cool_white",
    "slow_mood_beauty": "cinematic",
    "sweet_intro_hold": "sweet",
    "stage_beat_cut": "stage",
    "monochrome_to_color_beauty": "monochrome_beauty_reveal",
    "contrast_two_video": "contrast_special",
}


def template_profile_for(name_or_profile: str | None) -> dict[str, Any] | None:
    if not name_or_profile:
        return None
    key = ALIASES.get(name_or_profile, name_or_profile)
    profile = TEMPLATE_PROFILES.get(key)
    return deepcopy(profile) if profile else None


def apply_template_profile(style: dict[str, Any], template_name: str | None = None) -> dict[str, Any]:
    result = dict(style)
    profile = template_profile_for(template_name or result.get("template") or result.get("edit_profile"))
    if not profile:
        return result
    camera = profile["camera"]
    transition = profile["transition"]
    shot_range = camera.get("shot_duration_range") or []
    if len(shot_range) == 2:
        result["min_shot_duration"] = float(shot_range[0])
        result["max_shot_duration"] = float(shot_range[1])
        result["avg_shot_duration"] = round((float(shot_range[0]) + float(shot_range[1])) / 2, 2)
    result["template_profile"] = profile
    result["template_profile_id"] = profile["template_id"]
    result["template_profile_name"] = profile["template_name"]
    result["effect_intensity"] = _intensity_from_strength(max(camera.get("strength", 3), transition.get("strength", 3)))
    result["transition_style"] = transition.get("preferred", result.get("transition_style", []))
    result["render_profile"] = profile.get("render", {})
    result["template_constraints"] = profile.get("constraints", [])
    return result


def template_profile_catalog() -> list[dict[str, Any]]:
    return [deepcopy(profile) for profile in TEMPLATE_PROFILES.values()]


def _intensity_from_strength(strength: int | float) -> str:
    if float(strength) >= 8:
        return "strong"
    if float(strength) <= 3:
        return "subtle"
    return "medium"
