from fastapi import APIRouter, HTTPException

from app.models.schemas import ProjectRequest
from app.services.beat_analyzer import analyze_bgm as analyze_bgm_file
from app.services.clip_selector import select_candidate_clips
from app.services.frame_extractor import analyze_materials as analyze_video_materials
from app.services.project_store import get_project, save_project
from app.services.reference_analyzer import analyze_reference_video, default_style_template
from app.utils.file_utils import project_asset_dir, project_dir
from app.utils.json_utils import write_json

router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.post("/reference")
def analyze_reference(req: ProjectRequest):
    try:
        state = get_project(req.project_id)
        if state.reference:
            path = project_asset_dir("reference", state.project_id) / state.reference
            style = analyze_reference_video(path)
        else:
            style = default_style_template()
        state.reference_style = style
        state.status = "reference_analyzed"
        state.progress = max(state.progress, 30)
        save_project(state)
        write_json(project_dir(state.project_id) / "reference_style.json", style)
        return style
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/materials")
def analyze_materials(req: ProjectRequest):
    try:
        state = get_project(req.project_id)
        folder = project_asset_dir("raw_videos", state.project_id)
        video_paths = [folder / name for name in state.videos]
        frame_rows = analyze_video_materials(video_paths)
        candidates = select_candidate_clips(frame_rows)
        state.frame_analysis = frame_rows
        state.candidate_clips = candidates
        state.status = "materials_analyzed"
        state.progress = max(state.progress, 55)
        save_project(state)
        write_json(project_dir(state.project_id) / "frame_analysis.json", frame_rows)
        write_json(project_dir(state.project_id) / "candidate_clips.json", candidates)
        return {"frames": frame_rows, "candidate_clips": candidates}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/bgm")
def analyze_bgm(req: ProjectRequest, target_duration: int = 30):
    try:
        state = get_project(req.project_id)
        if not state.bgm:
            raise ValueError("BGM not uploaded")
        path = project_asset_dir("bgm", state.project_id) / state.bgm
        beats = analyze_bgm_file(path, target_duration=target_duration)
        state.beats = beats
        state.status = "bgm_analyzed"
        state.progress = max(state.progress, 65)
        save_project(state)
        write_json(project_dir(state.project_id) / "beats.json", beats)
        return beats
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
