from fastapi import APIRouter, HTTPException

from app.models.schemas import TimelineRequest
from app.services.aspect_ratio import normalize_aspect_ratio
from app.services.duration_policy import project_target_duration
from app.services.llm_planner import generate_timeline
from app.services.project_store import get_project, save_project
from app.services.reference_analyzer import default_style_template
from app.services.skill_retriever import apply_planner_context_to_style, retrieve_timeline_planner_context
from app.services.skill_registry import load_skills
from app.services.template_profile_catalog import apply_template_profile
from app.services.timeline_quality import build_timeline_quality_report
from app.utils.file_utils import project_dir
from app.utils.json_utils import write_json

router = APIRouter(tags=["timeline"])


@router.get("/skills")
def skills():
    return {"skills": load_skills()}


@router.post("/generate/timeline")
def create_timeline(req: TimelineRequest):
    try:
        state = get_project(req.project_id)
        aspect_ratio = normalize_aspect_ratio(req.aspect_ratio or state.aspect_ratio)
        state.aspect_ratio = aspect_ratio
        style = apply_template_profile(state.reference_style or default_style_template(req.style_template), req.style_template)
        style["aspect_ratio"] = aspect_ratio
        planner_context = retrieve_timeline_planner_context(req.project_id, req.style_template)
        style = apply_planner_context_to_style(style, planner_context)
        target_duration = project_target_duration(state, req.target_duration, style)
        beats = state.beats or {"beats": [i * 0.5 for i in range(1, target_duration * 2)], "strong_beats": [i * 2 for i in range(1, max(2, target_duration // 2))], "target_duration": target_duration}
        timeline = generate_timeline(style, state.candidate_clips, beats, target_duration, req.use_llm)
        timeline["aspect_ratio"] = aspect_ratio
        if beats.get("audio_duration_sec"):
            timeline["target_duration"] = float(beats["audio_duration_sec"])
            timeline["duration_policy"] = "match_bgm_audio_duration"
        timeline["planner_context"] = planner_context
        timeline["quality_report"] = build_timeline_quality_report(timeline, state.videos)
        state.reference_style = style
        state.timeline = timeline
        state.status = "timeline_generated"
        state.progress = max(state.progress, 78)
        save_project(state)
        write_json(project_dir(state.project_id) / "timeline.json", timeline)
        return timeline
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
