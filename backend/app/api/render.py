from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse

from app.models.schemas import EnhanceRequest, RenderRequest
from app.services.capcut_exporter import build_capcut_actions
from app.services.project_store import get_project, save_project
from app.services.render_history import archive_render_output, load_render_history, render_history_video_path
from app.services.video_enhancer import enhance_video, topaz_available
from app.services.video_renderer import render_video
from app.utils.file_utils import cleanup_project_sources, project_asset_dir
from app.utils.json_utils import write_json

router = APIRouter(tags=["render"])


@router.post("/render")
def render(req: RenderRequest, background_tasks: BackgroundTasks):
    try:
        state = get_project(req.project_id)
        if not state.timeline:
            raise ValueError("Timeline not generated")
        state.status = "rendering"
        state.progress = 85
        state.enhanced_output = None
        state.timeline.pop("render_error", None)
        state.timeline.pop("enhance_error", None)
        save_project(state)
        background_tasks.add_task(_render_job, req)
        return {"project_id": state.project_id, "status": state.status, "progress": state.progress}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _render_job(req: RenderRequest):
    state = get_project(req.project_id)
    try:
        source_dir = project_asset_dir("raw_videos", state.project_id)
        bgm_path = project_asset_dir("bgm", state.project_id) / state.bgm if state.bgm else None
        output_path = project_asset_dir("outputs", state.project_id) / "output.mp4"
        render_video(state.project_id, state.timeline, source_dir, bgm_path, output_path, req.keep_original_audio)
        state.output = output_path.name
        if req.archive_history:
            state.timeline = state.timeline or {}
            state.timeline["render_history_entry"] = archive_render_output(state, output_path)
        state.status = "done"
        state.progress = 100
        save_project(state)
        if req.cleanup_sources:
            cleanup_project_sources(state.project_id)
    except Exception as exc:
        state.status = "render_failed"
        state.progress = max(state.progress, 85)
        state.timeline = state.timeline or {}
        state.timeline["render_error"] = str(exc)
        save_project(state)


@router.get("/enhance/capabilities")
def enhance_capabilities():
    topaz = topaz_available()
    return {
        "topaz": topaz,
        "modes": [
            {"id": "ffmpeg_hq", "label": "内置高清修复", "available": True},
            {"id": "topaz", "label": "Topaz Video AI", "available": topaz["available"]},
        ],
        "presets": [
            {"id": "idol_stage_hq", "label": "爱豆舞台高清"},
            {"id": "soft_face_hq", "label": "柔和人像高清"},
            {"id": "sharp_stage_hq", "label": "高锐舞台高清"},
        ],
    }


@router.post("/enhance")
def enhance(req: EnhanceRequest, background_tasks: BackgroundTasks):
    try:
        state = get_project(req.project_id)
        output_path = project_asset_dir("outputs", state.project_id) / "output.mp4"
        if not output_path.exists():
            raise ValueError("Output video not found. Render the video before enhancement.")
        state.status = "enhancing"
        state.progress = 92
        state.timeline = state.timeline or {}
        state.timeline.pop("enhance_error", None)
        save_project(state)
        background_tasks.add_task(_enhance_job, req)
        return {"project_id": state.project_id, "status": state.status, "progress": state.progress}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _enhance_job(req: EnhanceRequest):
    state = get_project(req.project_id)
    try:
        input_path = project_asset_dir("outputs", state.project_id) / "output.mp4"
        output_path = project_asset_dir("outputs", state.project_id) / "enhanced_output.mp4"
        result = enhance_video(input_path, output_path, req.mode, req.preset)
        state.enhanced_output = output_path.name
        state.status = "enhanced"
        state.progress = 100
        state.timeline = state.timeline or {}
        state.timeline["enhance_result"] = result
        state.timeline.pop("enhance_error", None)
        save_project(state)
    except Exception as exc:
        state.status = "enhance_failed"
        state.progress = max(state.progress, 92)
        state.timeline = state.timeline or {}
        state.timeline["enhance_error"] = str(exc)
        save_project(state)


@router.get("/output/{project_id}")
def output(project_id: str):
    output_path = project_asset_dir("outputs", project_id) / "output.mp4"
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Output not found")
    return FileResponse(output_path, media_type="video/mp4", filename=f"{project_id}_fancut.mp4")


@router.get("/render/history/{project_id}")
def render_history(project_id: str):
    try:
        return {"project_id": project_id, "items": load_render_history(project_id)}
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/render/history/{project_id}/{version}")
def render_history_output(project_id: str, version: int):
    try:
        output_path = render_history_video_path(project_id, version)
        if not output_path.exists():
            raise FileNotFoundError(f"Archived output not found: {output_path}")
        return FileResponse(output_path, media_type="video/mp4", filename=f"{project_id}_fancut_v{version:03d}.mp4")
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/enhanced-output/{project_id}")
def enhanced_output(project_id: str):
    output_path = project_asset_dir("outputs", project_id) / "enhanced_output.mp4"
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Enhanced output not found")
    return FileResponse(output_path, media_type="video/mp4", filename=f"{project_id}_fancut_hq.mp4")


@router.get("/capcut/actions/{project_id}")
def capcut_actions(project_id: str):
    try:
        state = get_project(project_id)
        if not state.timeline:
            raise ValueError("Timeline not generated")
        actions = build_capcut_actions(state)
        output_path = project_asset_dir("outputs", project_id) / "capcut_actions.json"
        write_json(output_path, actions)
        return FileResponse(output_path, media_type="application/json", filename=f"{project_id}_capcut_actions.json")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
