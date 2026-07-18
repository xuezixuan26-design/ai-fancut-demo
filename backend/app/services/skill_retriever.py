from typing import Any

from app.services.knowledge_base import FRAME_SKILL_PATH
from app.utils.file_utils import project_dir
from app.utils.json_utils import read_json, write_json


def retrieve_timeline_planner_context(project_id: str, style_template: str | None = None) -> dict[str, Any]:
    project_path = project_dir(project_id)
    project_analysis = read_json(project_path / "frame_to_edit_analysis.json") or {}
    project_skill = project_analysis.get("learned_skill") or {}
    kb_frame_skills = read_json(FRAME_SKILL_PATH, default=[]) or []
    harness_scores = read_json(project_path / "harness_scores.json", default={}) or {}
    harness_report = read_json(project_path / "harness_report.json", default={}) or {}

    selected_frame_skills = _select_frame_skills(project_id, project_skill, kb_frame_skills)
    preferred_runs = _preferred_runs(harness_scores, harness_report)
    constraints = _build_constraints(selected_frame_skills, preferred_runs)
    context = {
        "schema": "ai-fancut.timeline-planner-context.v1",
        "project_id": project_id,
        "style_template": style_template,
        "sources": {
            "project_frame_analysis": bool(project_skill),
            "knowledge_base_frame_skills": len(kb_frame_skills),
            "harness_scores": len(harness_scores.get("scores", [])) if isinstance(harness_scores, dict) else 0,
            "harness_report": bool(harness_report),
        },
        "selected_frame_skills": selected_frame_skills,
        "preferred_runs": preferred_runs,
        "constraints": constraints,
    }
    write_json(project_path / "planner_context.json", context)
    return context


def apply_planner_context_to_style(reference_style: dict[str, Any], planner_context: dict[str, Any]) -> dict[str, Any]:
    style = dict(reference_style)
    constraints = planner_context.get("constraints") or {}
    if not constraints:
        return style

    style["planner_context"] = planner_context
    style["frame_skill_constraints"] = constraints

    if constraints.get("opening_strategy") == "atmosphere_reveal":
        style["opening_pattern"] = style.get("opening_pattern") or "slow_reveal_hook"
    if constraints.get("motion_strategy") == "micro_progressive_push":
        style["motion_profile"] = "slow_push"
    if constraints.get("cut_strategy") == "stable_micro_progression":
        style["cut_density"] = "medium"
        style["effect_intensity"] = "medium"
    if constraints.get("ending_strategy") == "memory_hold":
        style["ending_pattern"] = "memory_point_hold"

    preferred = constraints.get("preferred_style_template")
    if preferred and not style.get("retrieved_preferred_style"):
        style["retrieved_preferred_style"] = preferred
    return style


def _select_frame_skills(
    project_id: str,
    project_skill: dict[str, Any],
    kb_frame_skills: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    selected = []
    if project_skill:
        selected.append(
            {
                "scope": "project",
                "skill_id": project_skill.get("id"),
                "skill_name": project_skill.get("name"),
                "confidence": project_skill.get("confidence", 0),
                "detected_traits": project_skill.get("detected_traits", {}),
                "structure_rules": project_skill.get("structure_rules", []),
                "frame_relation_rules": project_skill.get("frame_relation_rules", []),
                "effect_mapping": project_skill.get("effect_mapping", {}),
                "avoid_rules": project_skill.get("avoid_rules", []),
            }
        )

    project_matches = [item for item in kb_frame_skills if item.get("project_id") == project_id]
    global_matches = [item for item in kb_frame_skills if item.get("project_id") != project_id]
    ranked = sorted(
        project_matches or global_matches,
        key=lambda item: float(item.get("confidence", 0) or 0),
        reverse=True,
    )
    for item in ranked[:3]:
        source_key = item.get("source_key")
        if any(existing.get("source_key") == source_key for existing in selected):
            continue
        selected.append(
            {
                "scope": "knowledge_base",
                "source_key": source_key,
                "skill_id": item.get("skill_id"),
                "skill_name": item.get("skill_name"),
                "confidence": item.get("confidence", 0),
                "detected_traits": item.get("detected_traits", {}),
                "structure_rules": item.get("structure_rules", []),
                "frame_relation_rules": item.get("frame_relation_rules", []),
                "effect_mapping": item.get("effect_mapping", {}),
                "avoid_rules": item.get("avoid_rules", []),
            }
        )
    return selected[:4]


def _preferred_runs(harness_scores: dict[str, Any], harness_report: dict[str, Any]) -> list[dict[str, Any]]:
    report_runs = {
        str(run.get("run_id") or run.get("style_template")): run
        for run in (harness_report.get("runs", []) if isinstance(harness_report, dict) else [])
    }
    scored = []
    for item in harness_scores.get("scores", []) if isinstance(harness_scores, dict) else []:
        run_id = str(item.get("run_id"))
        report_run = report_runs.get(run_id, {})
        scored.append(
            {
                "run_id": run_id,
                "style_template": report_run.get("style_template", run_id),
                "human_score": item.get("human_score"),
                "winner": bool(item.get("winner")),
                "liked": item.get("liked", []),
                "disliked": item.get("disliked", []),
                "model_score": report_run.get("model_score", report_run.get("score")),
                "effects": report_run.get("effects", []),
                "transitions": report_run.get("transitions", []),
            }
        )
    return sorted(scored, key=lambda item: (bool(item.get("winner")), float(item.get("human_score") or 0)), reverse=True)[:4]


def _build_constraints(frame_skills: list[dict[str, Any]], preferred_runs: list[dict[str, Any]]) -> dict[str, Any]:
    traits = _merge_traits(frame_skills)
    effect_mapping = _merge_effect_mapping(frame_skills)
    structure_rules = _merge_list(frame_skills, "structure_rules", 8)
    relation_rules = _merge_list(frame_skills, "frame_relation_rules", 8)
    avoid_rules = _merge_list(frame_skills, "avoid_rules", 8)
    preferred = preferred_runs[0] if preferred_runs else {}

    low_sat_opening = bool(traits.get("low_saturation_opening"))
    micro_share = float(traits.get("same_shot_micro_progression_share") or 0)
    closeup_share = float(traits.get("closeup_share") or 0)
    center_share = float(traits.get("center_or_near_center_share") or 0)
    return {
        "opening_strategy": "atmosphere_reveal" if low_sat_opening else "direct_subject_hook",
        "motion_strategy": "micro_progressive_push" if micro_share >= 0.45 else "beat_responsive_motion",
        "cut_strategy": "stable_micro_progression" if micro_share >= 0.45 else "rhythmic_variation",
        "shot_priority": _shot_priority(closeup_share, center_share),
        "ending_strategy": "memory_hold",
        "effect_mapping": effect_mapping,
        "structure_rules": structure_rules,
        "frame_relation_rules": relation_rules,
        "avoid_rules": avoid_rules,
        "preferred_style_template": preferred.get("style_template"),
        "preferred_effects": preferred.get("effects", []),
        "preferred_transitions": preferred.get("transitions", []),
        "human_preference_strength": float(preferred.get("human_score") or 0) / 10 if preferred else 0,
    }


def _merge_traits(frame_skills: list[dict[str, Any]]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    numeric_keys = [
        "closeup_share",
        "center_or_near_center_share",
        "same_shot_micro_progression_share",
    ]
    for key in numeric_keys:
        values = [
            float((skill.get("detected_traits") or {}).get(key) or 0)
            for skill in frame_skills
            if (skill.get("detected_traits") or {}).get(key) is not None
        ]
        if values:
            merged[key] = round(sum(values) / len(values), 3)
    merged["low_saturation_opening"] = any(
        bool((skill.get("detected_traits") or {}).get("low_saturation_opening"))
        for skill in frame_skills
    )
    trends = []
    for skill in frame_skills:
        trends.extend((skill.get("detected_traits") or {}).get("early_window_trends", []))
    merged["early_window_trends"] = sorted(set(trends))
    return merged


def _merge_effect_mapping(frame_skills: list[dict[str, Any]]) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {}
    for skill in frame_skills:
        for role, effects in (skill.get("effect_mapping") or {}).items():
            merged.setdefault(role, [])
            for effect in effects or []:
                if effect not in merged[role]:
                    merged[role].append(effect)
    return {role: effects[:5] for role, effects in merged.items()}


def _merge_list(frame_skills: list[dict[str, Any]], key: str, limit: int) -> list[str]:
    values = []
    for skill in frame_skills:
        for value in skill.get(key, []) or []:
            if value not in values:
                values.append(value)
    return values[:limit]


def _shot_priority(closeup_share: float, center_share: float) -> list[str]:
    priority = []
    if closeup_share >= 0.45:
        priority.extend(["closeup", "medium_closeup"])
    else:
        priority.extend(["medium_closeup", "half_body"])
    if center_share >= 0.6:
        priority.append("center_or_near_center")
    priority.append("high_highlight_score")
    return priority
