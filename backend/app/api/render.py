from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.models.schemas import RenderRequest
from app.services.project_store import get_project, save_project
from app.services.video_renderer import render_video
from app.utils.file_utils import project_asset_dir

router = APIRouter(tags=["render"])


@router.post("/render")
def render(req: RenderRequest):
    try:
        state = get_project(req.project_id)
        if not state.timeline:
            raise ValueError("Timeline not generated")
        source_dir = project_asset_dir("raw_videos", state.project_id)
        bgm_path = project_asset_dir("bgm", state.project_id) / state.bgm if state.bgm else None
        output_path = project_asset_dir("outputs", state.project_id) / "output.mp4"
        render_video(state.project_id, state.timeline, source_dir, bgm_path, output_path, req.keep_original_audio)
        state.output = output_path.name
        state.status = "done"
        state.progress = 100
        save_project(state)
        return {"project_id": state.project_id, "output_url": f"/api/output/{state.project_id}", "output": state.output}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/output/{project_id}")
def output(project_id: str):
    output_path = project_asset_dir("outputs", project_id) / "output.mp4"
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Output not found")
    return FileResponse(output_path, media_type="video/mp4", filename=f"{project_id}_fancut.mp4")
