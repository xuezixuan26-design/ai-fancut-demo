from __future__ import annotations

from typing import Any


CAMERA_MOTION_CATALOG: dict[str, dict[str, Any]] = {
    "slow_zoom_in": {
        "mode": "关键帧推镜",
        "category": "keyframe_camera",
        "keyframes": [{"t": 0.0, "scale": 1.0}, {"t": 1.0, "scale": 1.12}],
        "blur": False,
        "default_strength": 3,
    },
    "micro_push": {
        "mode": "智能推进",
        "category": "smart_camera",
        "keyframes": [{"t": 0.0, "scale": 1.0}, {"t": 1.0, "scale": 1.07}],
        "blur": False,
        "default_strength": 2,
    },
    "drift_zoom": {
        "mode": "缓慢变焦",
        "category": "effect_camera",
        "keyframes": [{"t": 0.0, "x": -0.02, "y": 0.0, "scale": 1.04}, {"t": 1.0, "x": 0.02, "y": -0.02, "scale": 1.12}],
        "blur": False,
        "default_strength": 3,
    },
    "breathing_zoom": {
        "mode": "呼吸缩放",
        "category": "smart_camera",
        "keyframes": [{"t": 0.0, "scale": 1.03}, {"t": 0.5, "scale": 1.09}, {"t": 1.0, "scale": 1.04}],
        "blur": False,
        "default_strength": 2,
    },
    "slight_zoom": {
        "mode": "智能推进",
        "category": "smart_camera",
        "keyframes": [{"t": 0.0, "scale": 1.0}, {"t": 1.0, "scale": 1.05}],
        "blur": False,
        "default_strength": 2,
    },
    "pan_left": {
        "mode": "关键帧横移",
        "category": "keyframe_camera",
        "keyframes": [{"t": 0.0, "x": 0.16, "scale": 1.12}, {"t": 1.0, "x": -0.16, "scale": 1.12}],
        "blur": False,
        "default_strength": 4,
    },
    "pan_right": {
        "mode": "关键帧横移",
        "category": "keyframe_camera",
        "keyframes": [{"t": 0.0, "x": -0.16, "scale": 1.12}, {"t": 1.0, "x": 0.16, "scale": 1.12}],
        "blur": False,
        "default_strength": 4,
    },
    "tilt_up": {
        "mode": "智能上移",
        "category": "smart_camera",
        "keyframes": [{"t": 0.0, "y": 0.12, "scale": 1.1}, {"t": 1.0, "y": -0.12, "scale": 1.1}],
        "blur": False,
        "default_strength": 4,
    },
    "tilt_down": {
        "mode": "智能下移",
        "category": "smart_camera",
        "keyframes": [{"t": 0.0, "y": -0.12, "scale": 1.1}, {"t": 1.0, "y": 0.12, "scale": 1.1}],
        "blur": False,
        "default_strength": 4,
    },
    "zoom_punch": {
        "mode": "冲击放大回弹",
        "category": "effect_camera",
        "keyframes": [{"t": 0.0, "scale": 1.0}, {"t": 0.35, "scale": 1.22}, {"t": 1.0, "scale": 1.08}],
        "blur": True,
        "default_strength": 7,
    },
    "snap_zoom": {
        "mode": "定点放大",
        "category": "smart_camera",
        "keyframes": [{"t": 0.0, "scale": 1.0}, {"t": 0.18, "scale": 1.3}, {"t": 1.0, "scale": 1.15}],
        "blur": True,
        "default_strength": 8,
    },
    "beat_shake": {
        "mode": "轻微动态抖动",
        "category": "smart_camera",
        "keyframes": [{"t": 0.0, "x": -0.03}, {"t": 0.5, "x": 0.03}, {"t": 1.0, "x": 0.0}],
        "blur": True,
        "default_strength": 7,
    },
    "whip_push": {
        "mode": "甩镜",
        "category": "physical_camera",
        "keyframes": [{"t": 0.0, "x": -0.12, "scale": 1.08}, {"t": 0.5, "x": 0.14, "scale": 1.24}, {"t": 1.0, "x": 0.0, "scale": 1.12}],
        "blur": True,
        "default_strength": 8,
    },
    "soft_glow": {
        "mode": "画面低频微晃",
        "category": "effect_camera",
        "keyframes": [{"t": 0.0, "scale": 1.02}, {"t": 1.0, "scale": 1.06}],
        "blur": False,
        "default_strength": 2,
    },
}

TRANSITION_CATALOG: dict[str, dict[str, Any]] = {
    "hard_cut": {"type": "基础线性转场-硬切", "duration": 0.0, "strength": 0, "blur": False, "light": False},
    "crossfade": {"type": "基础线性转场-叠化渐变", "duration": 0.28, "strength": 3, "blur": False, "light": False},
    "flash_white": {"type": "基础线性转场-闪白硬切", "duration": 0.16, "strength": 7, "blur": False, "light": True},
    "flash_black": {"type": "基础线性转场-闪黑硬切", "duration": 0.18, "strength": 6, "blur": False, "light": False},
    "soft_wash": {"type": "光效创意转场-柔光雾化", "duration": 0.34, "strength": 4, "blur": True, "light": True},
    "luma_fade": {"type": "基础线性转场-渐变灰度擦除", "duration": 0.3, "strength": 4, "blur": False, "light": False},
    "glow_flash": {"type": "光效创意转场-高光闪切", "duration": 0.24, "strength": 6, "blur": True, "light": True},
    "bloom_blur": {"type": "光效创意转场-柔光雾化", "duration": 0.32, "strength": 6, "blur": True, "light": True},
    "whip_pan": {"type": "运镜联动转场-急速模糊甩动转场", "duration": 0.28, "strength": 8, "blur": True, "light": False},
    "zoom_burst": {"type": "运镜联动转场-推近衔接转场", "duration": 0.34, "strength": 8, "blur": True, "light": True},
    "shake_zoom": {"type": "综艺卡通转场-画面抖动切镜", "duration": 0.32, "strength": 8, "blur": True, "light": False},
    "spin_blur": {"type": "运镜联动转场-旋转衔接", "duration": 0.38, "strength": 8, "blur": True, "light": False},
    "rotate_flash": {"type": "运镜联动转场-旋转衔接", "duration": 0.3, "strength": 7, "blur": True, "light": True},
    "strobe_white": {"type": "光效创意转场-高光闪切", "duration": 0.14, "strength": 9, "blur": False, "light": True},
    "whip_flash": {"type": "运镜联动转场-急速模糊甩动转场", "duration": 0.22, "strength": 8, "blur": True, "light": True},
}

CAMERA_MOTION_CATALOG.update(
    {
        "slow_motion_glow": {
            "mode": "缓慢推进",
            "category": "keyframe_camera",
            "keyframes": [{"t": 0.0, "scale": 1.02}, {"t": 1.0, "scale": 1.07}],
            "blur": True,
            "default_strength": 2,
        },
        "slowmo_beat_freeze": {
            "mode": "定点放大",
            "category": "effect_camera",
            "keyframes": [{"t": 0.0, "scale": 1.04}, {"t": 0.45, "scale": 1.12}, {"t": 1.0, "scale": 1.06}],
            "blur": True,
            "default_strength": 4,
        },
    }
)


def build_camera_instruction(effect: str, duration: float, clip_index: int, template_profile: dict[str, Any] | None = None) -> dict[str, Any]:
    spec = CAMERA_MOTION_CATALOG.get(effect, CAMERA_MOTION_CATALOG["slight_zoom"])
    template_camera = (template_profile or {}).get("camera") or {}
    strength = int(template_camera.get("strength", spec["default_strength"]))
    mode = template_camera.get("mode") or spec["mode"]
    blur = bool(template_camera.get("motion_blur", spec["blur"]))
    keyframes = template_camera.get("keyframes") or spec.get("keyframes", [])
    return {
        "syntax": f"运镜模式:{mode};时长:{round(max(0.1, duration), 2)}s;运动强度:{strength};模糊效果:{'开启' if blur else '关闭'};作用素材:{clip_index + 1:02d}",
        "mode": mode,
        "category": spec["category"],
        "duration": round(max(0.1, duration), 3),
        "strength": strength,
        "blur": blur,
        "target_clip": f"{clip_index + 1:02d}",
        "keyframes": keyframes,
    }


def build_transition_instruction(transition: str, index: int, template_profile: dict[str, Any] | None = None) -> dict[str, Any]:
    spec = TRANSITION_CATALOG.get(transition, TRANSITION_CATALOG["hard_cut"])
    template_transition = (template_profile or {}).get("transition") or {}
    duration_range = template_transition.get("duration_range") or []
    duration = round((float(duration_range[0]) + float(duration_range[1])) / 2, 3) if len(duration_range) == 2 else spec["duration"]
    transition_type = template_transition.get("type") or spec["type"]
    strength = int(template_transition.get("strength", spec["strength"]))
    light = bool(template_transition.get("light_overlay", spec["light"]))
    return {
        "syntax": (
            f"转场类型:{transition_type};过渡时长:{duration}s;强度:{strength};"
            f"光效叠加:{'开启' if light else '关闭'};衔接素材:前{index:02d},后{index + 1:02d}"
        ),
        "transition_type": transition_type,
        "duration": duration,
        "strength": strength,
        "blur": bool(spec["blur"]),
        "light_overlay": light,
        "from_clip": f"{index:02d}",
        "to_clip": f"{index + 1:02d}",
    }


def motion_transition_skill() -> dict[str, Any]:
    return {
        "skill_id": "standardized_camera_transition_language",
        "skill_name": "标准化运镜转场指令语言",
        "type": "technical",
        "goal": "把运镜和转场从模糊描述转换为剪映/CapCut 可执行的枚举、时长、强度、模糊、光效和关键帧参数。",
        "camera_modes": sorted({spec["mode"] for spec in CAMERA_MOTION_CATALOG.values()}),
        "transition_types": sorted({spec["type"] for spec in TRANSITION_CATALOG.values()}),
        "rules": [
            "每个镜头必须有一个标准运镜模式、持续时长、强度、模糊开关和作用素材编号。",
            "每个非硬切转场必须有分类-名称、过渡时长、强度、光效开关和前后素材编号。",
            "强拍/drop 段优先使用推近衔接、旋转衔接、甩动、回弹推拉；intro/outro 优先使用叠化、柔光雾化、灰度擦除。",
            "禁止只输出好看、高级、丝滑等不可执行词。",
        ],
    }
