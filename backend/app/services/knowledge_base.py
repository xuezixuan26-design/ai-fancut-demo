from collections import Counter
from typing import Any

from app.config import settings
from app.services.motion_transition_catalog import motion_transition_skill
from app.services.skill_registry import load_skills
from app.services.template_profile_catalog import template_profile_catalog
from app.utils.json_utils import read_json, write_json


KB_DIR = settings.storage_dir / "knowledge_base"
PROJECT_MEMORY_PATH = KB_DIR / "project_memories.json"
FRAME_SKILL_PATH = KB_DIR / "frame_to_edit_skills.json"


def upsert_project_memory(summary: dict[str, Any]) -> None:
    memories = read_json(PROJECT_MEMORY_PATH, default=[]) or []
    project_id = summary.get("project_id")
    memories = [item for item in memories if item.get("project_id") != project_id]
    memories.append(summary)
    memories = memories[-80:]
    write_json(PROJECT_MEMORY_PATH, memories)


def upsert_frame_to_edit_skill(analysis: dict[str, Any]) -> None:
    skills = read_json(FRAME_SKILL_PATH, default=[]) or []
    skill = analysis.get("learned_skill") or {}
    source_key = f"{analysis.get('project_id') or 'no_project'}::{analysis.get('frame_dir')}"
    entry = {
        "source_key": source_key,
        "project_id": analysis.get("project_id"),
        "frame_dir": analysis.get("frame_dir"),
        "frame_count": analysis.get("frame_count"),
        "ai_status": analysis.get("ai_status"),
        "skill_id": skill.get("id"),
        "skill_name": skill.get("name"),
        "confidence": skill.get("confidence"),
        "detected_traits": skill.get("detected_traits", {}),
        "structure_rules": skill.get("structure_rules", []),
        "frame_relation_rules": skill.get("frame_relation_rules", []),
        "effect_mapping": skill.get("effect_mapping", {}),
        "avoid_rules": skill.get("avoid_rules", []),
    }
    skills = [item for item in skills if item.get("source_key") != source_key]
    skills.append(entry)
    skills = skills[-120:]
    write_json(FRAME_SKILL_PATH, skills)


def build_knowledge_base_summary(compressed: bool = False) -> dict[str, Any]:
    skills = load_skills()
    technical_catalog = motion_transition_skill()
    template_profiles = template_profile_catalog()
    memories = read_json(PROJECT_MEMORY_PATH, default=[]) or []
    frame_skills = read_json(FRAME_SKILL_PATH, default=[]) or []
    profiles = Counter(
        str((memory.get("style_fingerprint") or {}).get("edit_profile", "unknown"))
        for memory in memories
    )
    feedback_signals = Counter(
        signal
        for memory in memories
        for signal in (memory.get("preference_delta") or {}).get("signals", [])
    )
    reuse_hints = Counter(
        hint
        for memory in memories
        for hint in memory.get("reuse_hints", [])
    )
    summary = {
        "schema": "ai-fancut.knowledge-base.v1",
        "skill_count": len(skills),
        "skills": [
            {
                "skill_id": skill.get("skill_id"),
                "skill_name": skill.get("skill_name"),
                "type": skill.get("type"),
                "goal": skill.get("goal"),
            }
            for skill in skills
        ],
        "technical_catalogs": [technical_catalog],
        "template_profiles": template_profiles,
        "project_memory_count": len(memories),
        "frame_skill_count": len(frame_skills),
        "edit_profiles": profiles.most_common(),
        "feedback_signals": feedback_signals.most_common(),
        "reuse_hints": reuse_hints.most_common(12),
        "latest_memories": memories[-5:],
        "latest_frame_skills": frame_skills[-5:],
    }
    if compressed:
        return compress_knowledge_base_summary(summary)
    return summary


def compress_knowledge_base_summary(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "ai-fancut.knowledge-base-compressed.v1",
        "source_schema": summary.get("schema"),
        "counts": {
            "skills": summary.get("skill_count", 0),
            "template_profiles": len(summary.get("template_profiles", []) or []),
            "technical_catalogs": len(summary.get("technical_catalogs", []) or []),
            "frame_skills": summary.get("frame_skill_count", 0),
            "project_memories": summary.get("project_memory_count", 0),
        },
        "skills": [_compress_skill(skill) for skill in summary.get("skills", [])],
        "template_profiles": [_compress_template_profile(profile) for profile in summary.get("template_profiles", [])],
        "technical_catalogs": [_compress_technical_catalog(catalog) for catalog in summary.get("technical_catalogs", [])],
        "reuse_hints": summary.get("reuse_hints", [])[:12],
        "edit_profiles": summary.get("edit_profiles", [])[:8],
        "feedback_signals": summary.get("feedback_signals", [])[:8],
        "latest_memories": [_compress_memory(memory) for memory in summary.get("latest_memories", [])[-5:]],
        "latest_frame_skills": [_compress_frame_skill(skill) for skill in summary.get("latest_frame_skills", [])[-5:]],
        "compression_policy": {
            "keep": "ids, names, roles, constraints, high-signal parameters, latest memories, latest frame skills",
            "drop": "long raw goals, full nested render dictionaries, full catalog enumerations beyond top-level names",
        },
    }


def _compress_skill(skill: dict[str, Any]) -> dict[str, Any]:
    return {
        "skill_id": skill.get("skill_id"),
        "skill_name": skill.get("skill_name"),
        "type": skill.get("type"),
        "goal": _short(skill.get("goal"), 90),
    }


def _compress_template_profile(profile: dict[str, Any]) -> dict[str, Any]:
    camera = profile.get("camera") or {}
    transition = profile.get("transition") or {}
    render = profile.get("render") or {}
    return {
        "template_id": profile.get("template_id"),
        "template_name": profile.get("template_name"),
        "positioning": _short(profile.get("positioning"), 80),
        "camera": {
            "mode": camera.get("mode"),
            "shot_duration_range": camera.get("shot_duration_range"),
            "strength": camera.get("strength"),
            "motion_blur": camera.get("motion_blur"),
        },
        "transition": {
            "type": transition.get("type"),
            "duration_range": transition.get("duration_range"),
            "strength": transition.get("strength"),
            "preferred": (transition.get("preferred") or [])[:5],
        },
        "render": {
            "filter": render.get("filter") or render.get("opening_filter"),
            "strength": render.get("strength"),
            "key_params": _render_key_params(render),
        },
        "constraints": (profile.get("constraints") or [])[:5],
        "material_fit": (profile.get("material_fit") or [])[:4],
    }


def _compress_technical_catalog(catalog: dict[str, Any]) -> dict[str, Any]:
    return {
        "skill_id": catalog.get("skill_id"),
        "skill_name": catalog.get("skill_name"),
        "goal": _short(catalog.get("goal"), 100),
        "camera_mode_count": len(catalog.get("camera_modes", []) or []),
        "transition_type_count": len(catalog.get("transition_types", []) or []),
        "camera_modes": (catalog.get("camera_modes") or [])[:10],
        "transition_types": (catalog.get("transition_types") or [])[:10],
        "rules": (catalog.get("rules") or [])[:4],
    }


def _compress_memory(memory: dict[str, Any]) -> dict[str, Any]:
    edit_summary = memory.get("edit_summary") or {}
    return {
        "project_id": memory.get("project_id"),
        "style_fingerprint": memory.get("style_fingerprint") or {},
        "duration": edit_summary.get("duration"),
        "total_items": edit_summary.get("total_items"),
        "top_roles": (edit_summary.get("top_roles") or [])[:4],
        "top_effects": (edit_summary.get("top_effects") or [])[:5],
        "top_transitions": (edit_summary.get("top_transitions") or [])[:5],
        "reuse_hints": (memory.get("reuse_hints") or [])[:6],
        "quality": edit_summary.get("quality") or {},
    }


def _compress_frame_skill(skill: dict[str, Any]) -> dict[str, Any]:
    return {
        "skill_id": skill.get("skill_id"),
        "skill_name": skill.get("skill_name"),
        "confidence": skill.get("confidence"),
        "frame_count": skill.get("frame_count"),
        "ai_status": skill.get("ai_status"),
        "detected_traits": skill.get("detected_traits") or {},
        "structure_rules": (skill.get("structure_rules") or [])[:3],
        "frame_relation_rules": (skill.get("frame_relation_rules") or [])[:3],
        "effect_mapping_keys": list((skill.get("effect_mapping") or {}).keys())[:6],
        "avoid_rules": (skill.get("avoid_rules") or [])[:3],
    }


def _render_key_params(render: dict[str, Any]) -> dict[str, Any]:
    priority = [
        "temperature",
        "saturation",
        "brightness",
        "contrast",
        "highlight",
        "sharpen",
        "skin_smooth",
        "vignette",
        "film_grain",
        "particle",
        "particle_opacity",
    ]
    return {key: render[key] for key in priority if key in render}


def _short(value: Any, limit: int) -> str:
    text = "" if value is None else str(value)
    return text if len(text) <= limit else f"{text[:limit]}..."
