from fastapi import APIRouter, HTTPException

from app.models.schemas import TimelineRequest
from app.services.llm_planner import generate_timeline
from app.services.project_store import get_project, save_project
from app.services.reference_analyzer import default_style_template
from app.utils.file_utils import project_dir
from app.utils.json_utils import write_json

router = APIRouter(tags=["timeline"])


@router.post("/generate/timeline")
def create_timeline(req: TimelineRequest):
    try:
        state = get_project(req.project_id)
        style = state.reference_style or default_style_template(req.style_template)
        beats = state.beats or {"beats": [i * 0.5 for i in range(1, req.target_duration * 2)], "strong_beats": [i * 2 for i in range(1, 16)], "target_duration": req.target_duration}
        timeline = generate_timeline(style, state.candidate_clips, beats, req.target_duration, req.use_llm)
        state.reference_style = style
        state.timeline = timeline
        state.status = "timeline_generated"
        state.progress = max(state.progress, 78)
        save_project(state)
        write_json(project_dir(state.project_id) / "timeline.json", timeline)
        return timeline
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
