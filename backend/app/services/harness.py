import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.models.schemas import ProjectState
from app.services.duration_policy import project_target_duration
from app.services.llm_planner import generate_timeline
from app.services.project_store import save_project
from app.services.reference_analyzer import default_style_template
from app.services.skill_retriever import apply_planner_context_to_style, retrieve_timeline_planner_context
from app.services.timeline_quality import build_timeline_quality_report
from app.services.video_renderer import render_video
from app.utils.file_utils import project_asset_dir, project_dir, safe_filename
from app.utils.json_utils import read_json, write_json


DEFAULT_HARNESS_STYLES = [
    "korean_cool_white",
    "progressive_idol_beauty",
    "contrast_special",
    "monochrome_beauty_reveal",
    "stage",
]


def run_timeline_harness(
    state: ProjectState,
    style_templates: list[str] | None = None,
    target_duration: int | None = None,
) -> dict[str, Any]:
    styles = style_templates or DEFAULT_HARNESS_STYLES
    duration = project_target_duration(state, target_duration, fallback=20)
    beats = state.beats or _fallback_beats(duration)

    runs = []
    for style_name in styles:
        run_id = safe_filename(style_name)
        planner_context = retrieve_timeline_planner_context(state.project_id, style_name)
        style = apply_planner_context_to_style(default_style_template(style_name), planner_context)
        style["aspect_ratio"] = state.aspect_ratio
        timeline = generate_timeline(style, state.candidate_clips, beats, duration, use_llm=False)
        timeline["aspect_ratio"] = state.aspect_ratio
        quality = build_timeline_quality_report(timeline, state.videos)
        timeline["quality_report"] = quality
        score = _score_timeline(quality)
        evidence = _evidence_summary(state, style_name, timeline, quality, planner_context, rendered=False)
        runs.append(
            {
                "run_id": run_id,
                "style_template": style_name,
                "edit_profile": style.get("edit_profile"),
                "style_fingerprint": timeline.get("style_fingerprint", {}),
                "planner_constraints": planner_context.get("constraints", {}),
                "score": score,
                "explanation": _run_explanation(style_name, score, quality, planner_context),
                "trajectory": _run_trajectory(style_name, planner_context, timeline, quality, evidence, rendered=False),
                "evidence": evidence,
                "version_manifest": _version_manifest(),
                "quality_report": quality,
                "edit_decisions": timeline.get("edit_decisions", {}),
                "effects": _unique_values(timeline, "effect"),
                "transitions": _unique_values(timeline, "transition"),
                "timeline_preview": timeline.get("timeline", [])[:8],
            }
        )

    runs = sorted(runs, key=lambda item: item["score"], reverse=True)
    comparison = _comparison_summary(runs)
    report = {
        "schema": "ai-fancut.harness-report.v1",
        "project_id": state.project_id,
        "created_at": _now_iso(),
        "harness_goal": "record_evaluate_reproduce_debug_agent_pipeline",
        "input_fingerprint": _input_fingerprint(state, styles, duration),
        "version_manifest": _version_manifest(),
        "target_duration": duration,
        "aspect_ratio": state.aspect_ratio,
        "run_count": len(runs),
        "recommended_style": runs[0]["style_template"] if runs else None,
        "comparison_summary": comparison,
        "runs": runs,
    }
    write_json(project_dir(state.project_id) / "harness_report.json", report)
    return report


def run_preview_harness(
    state: ProjectState,
    style_templates: list[str] | None = None,
    target_duration: int = 12,
    render: bool = True,
) -> dict[str, Any]:
    styles = style_templates or DEFAULT_HARNESS_STYLES
    duration = max(3, min(int(target_duration or 12), 30))
    beats = state.beats or _fallback_beats(duration)
    source_dir = project_asset_dir("raw_videos", state.project_id)
    bgm_path = None
    if state.bgm:
        candidate = project_asset_dir("bgm", state.project_id) / state.bgm
        bgm_path = candidate if candidate.exists() else None
    preview_dir = project_asset_dir("outputs", state.project_id) / "harness_previews"
    preview_dir.mkdir(parents=True, exist_ok=True)

    previous_scores = _score_index(state.project_id)
    runs = []
    for style_name in styles:
        run_id = safe_filename(style_name)
        planner_context = retrieve_timeline_planner_context(state.project_id, style_name)
        style = apply_planner_context_to_style(default_style_template(style_name), planner_context)
        style["aspect_ratio"] = state.aspect_ratio
        full_timeline = generate_timeline(style, state.candidate_clips, beats, duration, use_llm=False)
        timeline = _limit_timeline(full_timeline, duration)
        timeline["aspect_ratio"] = state.aspect_ratio
        quality = build_timeline_quality_report(timeline, state.videos)
        score = _score_timeline(quality)
        human = previous_scores.get(run_id)
        if human and human.get("human_score") is not None:
            score = round(score * 0.7 + float(human["human_score"]) * 10 * 0.3, 2)

        preview_url = None
        output_file = None
        existing_output = preview_dir / f"{run_id}_preview.mp4"
        if render:
            output_path = existing_output
            render_video(state.project_id, timeline, source_dir, bgm_path, output_path, keep_original_audio=False)
            output_file = str(output_path)
            preview_url = f"/api/harness/preview/{state.project_id}/{output_path.name}"
        elif existing_output.exists():
            output_file = str(existing_output)
            preview_url = f"/api/harness/preview/{state.project_id}/{existing_output.name}"

        evidence = _evidence_summary(state, style_name, timeline, quality, planner_context, rendered=bool(output_file))
        runs.append(
            {
                "run_id": run_id,
                "style_template": style_name,
                "edit_profile": style.get("edit_profile"),
                "style_fingerprint": timeline.get("style_fingerprint", {}),
                "planner_constraints": planner_context.get("constraints", {}),
                "score": score,
                "model_score": _score_timeline(quality),
                "explanation": _run_explanation(style_name, score, quality, planner_context),
                "trajectory": _run_trajectory(style_name, planner_context, timeline, quality, evidence, rendered=bool(output_file)),
                "evidence": evidence,
                "version_manifest": _version_manifest(),
                "human_feedback": human,
                "quality_report": quality,
                "edit_decisions": timeline.get("edit_decisions", {}),
                "effects": _unique_values(timeline, "effect"),
                "transitions": _unique_values(timeline, "transition"),
                "timeline_preview": timeline.get("timeline", [])[:8],
                "preview_file": output_file,
                "preview_url": preview_url,
            }
        )

    runs = sorted(runs, key=lambda item: item["score"], reverse=True)
    comparison = _comparison_summary(runs)
    report = {
        "schema": "ai-fancut.preview-harness-report.v1",
        "project_id": state.project_id,
        "created_at": _now_iso(),
        "harness_goal": "record_evaluate_reproduce_debug_agent_pipeline",
        "input_fingerprint": _input_fingerprint(state, styles, duration),
        "version_manifest": _version_manifest(),
        "target_duration": duration,
        "aspect_ratio": state.aspect_ratio,
        "rendered": bool(render),
        "run_count": len(runs),
        "recommended_style": runs[0]["style_template"] if runs else None,
        "comparison_summary": comparison,
        "runs": runs,
        "operation": [
            "Generate several candidate timelines from reusable skills/templates.",
            "Render each candidate as a short preview under storage/outputs/{project_id}/harness_previews.",
            "Score by repeat risk, source diversity, crop stability, warnings, and optional human feedback.",
        ],
    }
    write_json(project_dir(state.project_id) / "harness_preview_report.json", report)
    write_json(project_dir(state.project_id) / "harness_report.json", report)
    return report


def save_harness_score(
    project_id: str,
    run_id: str,
    human_score: float | None = None,
    liked: list[str] | None = None,
    disliked: list[str] | None = None,
    winner: bool = False,
    notes: str = "",
) -> dict[str, Any]:
    score_path = project_dir(project_id) / "harness_scores.json"
    existing = read_json(score_path) or {"schema": "ai-fancut.harness-scores.v1", "project_id": project_id, "scores": []}
    scores = [item for item in existing.get("scores", []) if item.get("run_id") != run_id]
    if human_score is not None:
        human_score = max(0.0, min(float(human_score), 10.0))
    entry = {
        "run_id": run_id,
        "human_score": human_score,
        "liked": liked or [],
        "disliked": disliked or [],
        "winner": bool(winner),
        "notes": notes,
    }
    scores.append(entry)
    existing["scores"] = scores
    write_json(score_path, existing)
    report = _apply_score_to_report(project_id, entry)
    if report:
        existing["updated_report"] = report
    return existing


def promote_harness_run(
    state: ProjectState,
    run_id: str | None = None,
    target_duration: int | None = None,
) -> dict[str, Any]:
    report = read_json(project_dir(state.project_id) / "harness_report.json") or {}
    runs = report.get("runs") or []
    if not runs:
        raise ValueError("Harness report has no runs to promote.")

    selected = _select_promote_run(runs, run_id or report.get("recommended_style"))
    style_name = str(selected.get("style_template") or selected.get("run_id"))
    duration = project_target_duration(state, target_duration or report.get("target_duration"), fallback=20)
    beats = state.beats or _fallback_beats(duration)
    planner_context = retrieve_timeline_planner_context(state.project_id, style_name)
    style = apply_planner_context_to_style(default_style_template(style_name), planner_context)
    style["aspect_ratio"] = state.aspect_ratio
    timeline = generate_timeline(style, state.candidate_clips, beats, duration, use_llm=False)
    timeline["aspect_ratio"] = state.aspect_ratio
    if beats.get("audio_duration_sec"):
        timeline["target_duration"] = float(beats["audio_duration_sec"])
        timeline["duration_policy"] = "match_bgm_audio_duration"
    timeline["planner_context"] = planner_context
    timeline["quality_report"] = build_timeline_quality_report(timeline, state.videos)
    timeline["promoted_from_harness"] = {
        "run_id": selected.get("run_id") or selected.get("style_template"),
        "style_template": style_name,
        "score": selected.get("score"),
        "model_score": selected.get("model_score"),
        "human_feedback": selected.get("human_feedback"),
        "comparison_winner": report.get("recommended_style"),
    }

    state.reference_style = style
    state.timeline = timeline
    state.status = "timeline_promoted"
    state.progress = max(state.progress, 82)
    save_project(state)
    write_json(project_dir(state.project_id) / "timeline.json", timeline)
    write_json(project_dir(state.project_id) / "promoted_harness_timeline.json", timeline)
    return {
        "schema": "ai-fancut.harness-promote.v1",
        "project_id": state.project_id,
        "promoted_style": style_name,
        "target_duration": duration,
        "timeline_items": len(timeline.get("timeline", [])),
        "quality_report": timeline.get("quality_report"),
        "timeline": timeline,
    }


def _fallback_beats(duration: int) -> dict[str, Any]:
    return {
        "beats": [round(i * 0.5, 3) for i in range(1, duration * 2)],
        "strong_beats": [round(i * 2.0, 3) for i in range(1, max(2, duration // 2))],
        "target_duration": duration,
    }


def _select_promote_run(runs: list[dict[str, Any]], run_id: str | None) -> dict[str, Any]:
    if run_id:
        for run in runs:
            if str(run.get("run_id") or run.get("style_template")) == str(run_id) or str(run.get("style_template")) == str(run_id):
                return run
    return runs[0]


def _score_timeline(quality: dict[str, Any]) -> float:
    score = 100.0
    score += float(quality.get("timeline_source_diversity") or 0) * 12
    score += float(quality.get("timeline_source_family_diversity") or 0) * 10
    score += float(quality.get("crop_center_coverage") or 0) * 8
    score -= float(quality.get("top_source_share") or 0) * 18
    score -= float(quality.get("top_source_family_share") or 0) * 14
    score -= float(quality.get("consecutive_repeat_count") or 0) * 3
    score -= float(quality.get("effect_repeat_count") or 0) * 2
    score -= float(quality.get("transition_repeat_count") or 0) * 1.5
    score += (float(quality.get("music_picture_score") or 100) - 100) * 0.45
    score -= len(((quality.get("slow_motion") or {}).get("violations") or [])) * 6
    score -= len(quality.get("warnings") or []) * 4
    return round(max(0.0, score), 2)


def _unique_values(timeline: dict[str, Any], key: str) -> list[str]:
    values = []
    for item in timeline.get("timeline", []) or []:
        value = str(item.get(key, ""))
        if value and value not in values:
            values.append(value)
    return values


def _run_explanation(
    style_name: str,
    score: float,
    quality: dict[str, Any],
    planner_context: dict[str, Any],
) -> dict[str, Any]:
    music = quality.get("music_picture") or {}
    positives = []
    negatives = []
    if quality.get("timeline_source_diversity", 0) >= 0.8:
        positives.append("素材覆盖较均衡")
    if quality.get("crop_center_coverage", 0) >= 0.85:
        positives.append("主体裁切信息完整")
    if music.get("strong_beat_hit_rate", 0) >= 0.7:
        positives.append("强拍有明确视觉变化")
    if music.get("drop_visual_change_avg", 0) >= 0.6:
        positives.append("drop 段视觉抬升明显")
    if planner_context.get("constraints"):
        positives.append("已应用 frame-to-edit 检索约束")

    if quality.get("top_source_share", 0) > 0.42:
        negatives.append("单一素材占比偏高")
    if quality.get("effect_repeat_count", 0) > 0:
        negatives.append("存在连续效果重复")
    if quality.get("transition_repeat_count", 0) > 0:
        negatives.append("存在连续转场重复")
    if music.get("weak_section_overcut_count", 0) > 1:
        negatives.append("弱段强效果偏多")
    if music.get("strong_beat_hit_rate", 1) < 0.55:
        negatives.append("强拍视觉反馈不足")

    return {
        "style_template": style_name,
        "score_note": _score_note(score),
        "why_good": positives[:5],
        "why_risky": negatives[:5],
        "music_picture": {
            "score": quality.get("music_picture_score"),
            "strong_beat_hit_rate": music.get("strong_beat_hit_rate"),
            "drop_visual_change_avg": music.get("drop_visual_change_avg"),
            "weak_section_overcut_count": music.get("weak_section_overcut_count"),
        },
        "selected_constraints": {
            "opening_strategy": (planner_context.get("constraints") or {}).get("opening_strategy"),
            "cut_strategy": (planner_context.get("constraints") or {}).get("cut_strategy"),
            "motion_strategy": (planner_context.get("constraints") or {}).get("motion_strategy"),
        },
    }


def _run_trajectory(
    style_name: str,
    planner_context: dict[str, Any],
    timeline: dict[str, Any],
    quality: dict[str, Any],
    evidence: dict[str, Any],
    rendered: bool,
) -> list[dict[str, Any]]:
    constraints = planner_context.get("constraints") or {}
    items = timeline.get("timeline", []) or []
    return [
        _trace_step(
            1,
            "input_sample",
            "Need candidate edit variants before choosing a final vertical-domain edit.",
            "load_project_assets",
            {
                "candidate_clip_count": evidence["inputs"]["candidate_clip_count"],
                "source_count": evidence["inputs"]["source_count"],
                "target_duration": timeline.get("target_duration"),
                "aspect_ratio": timeline.get("aspect_ratio"),
            },
            ["project_state", "candidate_clips", "beats"],
        ),
        _trace_step(
            2,
            "skill_retrieval",
            "Retrieve reusable editing constraints and prior preference signals for this style.",
            "retrieve_timeline_planner_context",
            {
                "style_template": style_name,
                "constraint_keys": sorted(constraints.keys())[:12],
                "harness_scores_seen": (planner_context.get("sources") or {}).get("harness_scores"),
                "has_prior_report": (planner_context.get("sources") or {}).get("harness_report"),
            },
            ["skill_registry", "frame_skills", "project_memory", "harness_scores"],
        ),
        _trace_step(
            3,
            "timeline_planning",
            "Generate a timeline from selected clips, BGM beats, style constraints, aspect ratio, and slow-motion policy.",
            "generate_timeline",
            {
                "timeline_items": len(items),
                "effects": _unique_values(timeline, "effect")[:8],
                "transitions": _unique_values(timeline, "transition")[:8],
                "slow_motion": (quality.get("slow_motion") or {}),
            },
            ["timeline", "style_fingerprint", "edit_decisions"],
        ),
        _trace_step(
            4,
            "evidence_verification",
            "Verify the edit can be explained by measurable evidence instead of only final output impression.",
            "build_timeline_quality_report",
            {
                "warnings": quality.get("warnings", []),
                "music_picture": quality.get("music_picture", {}),
                "source_usage": quality.get("source_usage", {}),
                "source_family_usage": quality.get("source_family_usage", {}),
                "crop_center_coverage": quality.get("crop_center_coverage"),
            },
            ["quality_report", "music_picture", "slow_motion_report"],
        ),
        _trace_step(
            5,
            "scoring",
            "Score candidates for regression comparison and later human override.",
            "score_timeline",
            {
                "model_score_inputs": evidence["score_inputs"],
                "score_formula": "diversity + crop + music_picture - repeats - warnings - slow_motion_violations",
            },
            ["quality_report", "score"],
        ),
        _trace_step(
            6,
            "render_or_replay",
            "Render preview when requested; otherwise keep deterministic timeline for replay/debug.",
            "render_video" if rendered else "skip_render",
            {"rendered": rendered},
            ["preview_file", "timeline_preview"],
        ),
    ]


def _trace_step(
    index: int,
    name: str,
    thought: str,
    action: str,
    observation: dict[str, Any],
    evidence_refs: list[str],
) -> dict[str, Any]:
    return {
        "step": index,
        "name": name,
        "thought": thought,
        "action": action,
        "observation": observation,
        "evidence_refs": evidence_refs,
        "status": "ok",
    }


def _evidence_summary(
    state: ProjectState,
    style_name: str,
    timeline: dict[str, Any],
    quality: dict[str, Any],
    planner_context: dict[str, Any],
    rendered: bool,
) -> dict[str, Any]:
    music = quality.get("music_picture") or {}
    slow = quality.get("slow_motion") or {}
    return {
        "style_template": style_name,
        "inputs": {
            "project_id": state.project_id,
            "aspect_ratio": timeline.get("aspect_ratio") or state.aspect_ratio,
            "source_count": len(state.videos),
            "candidate_clip_count": len(state.candidate_clips or []),
            "has_bgm": bool(state.bgm),
            "has_reference": bool(state.reference),
        },
        "retrieval": {
            "sources": planner_context.get("sources") or {},
            "constraints": planner_context.get("constraints") or {},
        },
        "timeline": {
            "target_duration": timeline.get("target_duration"),
            "item_count": len(timeline.get("timeline", []) or []),
            "effects": _unique_values(timeline, "effect"),
            "transitions": _unique_values(timeline, "transition"),
            "slow_clip_indexes": slow.get("slow_clip_indexes", []),
        },
        "verification": {
            "warnings": quality.get("warnings", []),
            "music_picture_score": quality.get("music_picture_score"),
            "strong_beat_hit_rate": music.get("strong_beat_hit_rate"),
            "drop_visual_change_avg": music.get("drop_visual_change_avg"),
            "slow_motion_violations": slow.get("violations", []),
        },
        "score_inputs": {
            "timeline_source_diversity": quality.get("timeline_source_diversity"),
            "timeline_source_family_diversity": quality.get("timeline_source_family_diversity"),
            "crop_center_coverage": quality.get("crop_center_coverage"),
            "top_source_share": quality.get("top_source_share"),
            "top_source_family_share": quality.get("top_source_family_share"),
            "effect_repeat_count": quality.get("effect_repeat_count"),
            "transition_repeat_count": quality.get("transition_repeat_count"),
            "warning_count": len(quality.get("warnings") or []),
            "slow_motion_violation_count": len(slow.get("violations") or []),
        },
        "rendered": rendered,
    }


def _version_manifest() -> dict[str, Any]:
    return {
        "schema": "ai-fancut.harness-version.v1",
        "harness": "trajectory-evidence-v1",
        "planner": "local_timeline_planner_with_slow_motion_policy_v1",
        "quality_verifier": "timeline_quality_music_picture_slow_motion_v1",
        "renderer": "ffmpeg_segment_renderer_v2",
        "scoring": "model_score_with_human_override_v1",
    }


def _input_fingerprint(state: ProjectState, styles: list[str], duration: int) -> str:
    payload = {
        "project_id": state.project_id,
        "aspect_ratio": state.aspect_ratio,
        "videos": state.videos,
        "bgm": state.bgm,
        "reference": state.reference,
        "candidate_clip_count": len(state.candidate_clips or []),
        "beats_count": len((state.beats or {}).get("beats", [])),
        "strong_beats_count": len((state.beats or {}).get("strong_beats", [])),
        "styles": styles,
        "duration": duration,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _score_note(score: float) -> str:
    if score >= 95:
        return "recommended"
    if score >= 84:
        return "usable_with_review"
    return "needs_iteration"


def _comparison_summary(runs: list[dict[str, Any]]) -> dict[str, Any]:
    if not runs:
        return {"winner": None, "main_differences": [], "next_actions": []}
    winner = runs[0]
    differences = []
    for run in runs[1:4]:
        differences.append(
            {
                "style_template": run.get("style_template"),
                "score_delta": round(float(winner.get("score", 0)) - float(run.get("score", 0)), 2),
                "winner_advantage": _advantage(winner, run),
            }
        )
    next_actions = []
    winner_quality = winner.get("quality_report") or {}
    if winner_quality.get("effect_repeat_count", 0):
        next_actions.append("降低连续效果重复")
    if (winner_quality.get("music_picture") or {}).get("drop_visual_change_avg", 1) < 0.6:
        next_actions.append("提高 drop 段视觉变化")
    if winner_quality.get("top_source_share", 0) > 0.42:
        next_actions.append("增加素材轮换冷却")
    return {
        "winner": winner.get("style_template"),
        "winner_score": winner.get("score"),
        "main_differences": differences,
        "next_actions": next_actions or ["保留当前候选作为主版本，再做人工评分确认"],
    }


def _advantage(winner: dict[str, Any], other: dict[str, Any]) -> list[str]:
    win_q = winner.get("quality_report") or {}
    other_q = other.get("quality_report") or {}
    reasons = []
    if win_q.get("music_picture_score", 0) > other_q.get("music_picture_score", 0):
        reasons.append("音乐画面关系更强")
    if win_q.get("effect_repeat_count", 0) < other_q.get("effect_repeat_count", 0):
        reasons.append("效果重复更少")
    if win_q.get("top_source_share", 1) < other_q.get("top_source_share", 1):
        reasons.append("素材使用更均衡")
    if win_q.get("crop_center_coverage", 0) > other_q.get("crop_center_coverage", 0):
        reasons.append("主体裁切更稳定")
    return reasons or ["综合分更高"]


def _limit_timeline(timeline: dict[str, Any], target_duration: int) -> dict[str, Any]:
    copied = dict(timeline)
    limited = []
    elapsed = 0.0
    for raw in timeline.get("timeline", []) or []:
        item = dict(raw)
        try:
            start = float(item.get("start", 0))
            end = float(item.get("end", start + 0.1))
            speed = max(0.2, min(4.0, float(item.get("speed", 1.0) or 1.0)))
        except (TypeError, ValueError):
            continue
        source_duration = max(0.05, end - start)
        output_duration = source_duration / speed
        if elapsed + output_duration > target_duration:
            remaining = max(0.25, target_duration - elapsed)
            item["end"] = round(start + remaining * speed, 3)
            limited.append(item)
            break
        limited.append(item)
        elapsed += output_duration
        if elapsed >= target_duration:
            break
    copied["timeline"] = limited
    copied["target_duration"] = target_duration
    return copied


def _score_index(project_id: str) -> dict[str, dict[str, Any]]:
    score_doc = read_json(project_dir(project_id) / "harness_scores.json") or {}
    return {str(item.get("run_id")): item for item in score_doc.get("scores", [])}


def _apply_score_to_report(project_id: str, entry: dict[str, Any]) -> dict[str, Any] | None:
    report_path = project_dir(project_id) / "harness_report.json"
    report = read_json(report_path)
    if not report or not report.get("runs"):
        return None

    for run in report.get("runs", []):
        if str(run.get("run_id") or run.get("style_template")) != str(entry.get("run_id")):
            continue
        run["human_feedback"] = entry
        if entry.get("human_score") is not None:
            model_score = float(run.get("model_score", run.get("score", 0)) or 0)
            human_score = float(entry["human_score"]) * 10
            run["score"] = round(model_score * 0.65 + human_score * 0.35, 2)
        if entry.get("winner"):
            run["score"] = max(float(run.get("score", 0) or 0), 101.0)

    report["runs"] = sorted(report.get("runs", []), key=lambda item: float(item.get("score", 0) or 0), reverse=True)
    report["recommended_style"] = report["runs"][0].get("style_template") if report["runs"] else None
    write_json(report_path, report)
    preview_report_path = project_dir(project_id) / "harness_preview_report.json"
    if preview_report_path.exists():
        write_json(preview_report_path, report)
    return report
