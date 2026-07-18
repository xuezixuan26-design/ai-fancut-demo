from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.services.project_store import get_or_create_project, save_project
from app.utils.file_utils import AUDIO_EXTS, VIDEO_EXTS, project_asset_dir, save_upload

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/videos")
async def upload_videos(project_id: str | None = Form(default=None), files: list[UploadFile] = File(...)):
    try:
        state = get_or_create_project(project_id)
        folder = project_asset_dir("raw_videos", state.project_id)
        saved = []
        for file in files:
            path = await save_upload(file, folder, VIDEO_EXTS)
            saved.append(path.name)
        existing = [name for name in state.videos if (folder / name).exists()]
        state.videos = [*existing, *saved]
        _reset_generated_state(state, clear_material_analysis=True)
        state.status = "videos_uploaded"
        state.progress = max(state.progress, 10)
        save_project(state)
        return {"project_id": state.project_id, "videos": state.videos}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/bgm")
async def upload_bgm(project_id: str = Form(...), file: UploadFile = File(...)):
    try:
        state = get_or_create_project(project_id)
        path = await save_upload(file, project_asset_dir("bgm", state.project_id), AUDIO_EXTS | VIDEO_EXTS)
        state.bgm = path.name
        state.beats = None
        _reset_generated_state(state)
        state.status = "bgm_uploaded"
        state.progress = max(state.progress, 20)
        save_project(state)
        return {"project_id": state.project_id, "bgm": state.bgm}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/reference")
async def upload_reference(project_id: str = Form(...), file: UploadFile = File(...)):
    try:
        state = get_or_create_project(project_id)
        path = await save_upload(file, project_asset_dir("reference", state.project_id), VIDEO_EXTS)
        state.reference = path.name
        state.reference_style = None
        _reset_generated_state(state)
        state.status = "reference_uploaded"
        save_project(state)
        return {"project_id": state.project_id, "reference": state.reference}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _reset_generated_state(state, clear_material_analysis: bool = False) -> None:
    if clear_material_analysis:
        state.frame_analysis = []
        state.candidate_clips = []
    state.timeline = None
    state.output = None
    state.enhanced_output = None
    output_dir = project_asset_dir("outputs", state.project_id)
    for filename in ["output.mp4", "enhanced_output.mp4", "capcut_actions.json"]:
        path = output_dir / filename
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass
