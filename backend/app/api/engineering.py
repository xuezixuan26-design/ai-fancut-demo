from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.models.schemas import (
    ContextCompressRequest,
    CriticRequest,
    FrameAnalyzeRequest,
    HarnessPromoteRequest,
    HarnessPreviewRequest,
    HarnessRunRequest,
    HarnessScoreRequest,
)
from app.services.context_compressor import compress_project_context
from app.services.edit_critic import critique_project_edit, revise_timeline_from_critic
from app.services.frame_to_edit_analyzer import analyze_frame_directory
from app.services.harness import promote_harness_run, run_preview_harness, run_timeline_harness, save_harness_score
from app.services.knowledge_base import build_knowledge_base_summary
from app.services.project_store import get_project
from app.services.project_store import save_project
from app.utils.file_utils import project_asset_dir, project_dir
from app.utils.json_utils import read_json

router = APIRouter(tags=["engineering"])


@router.post("/context/compress")
def compress_context(req: ContextCompressRequest):
    try:
        state = get_project(req.project_id)
        return compress_project_context(state, req.feedback)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/context/summary/{project_id}")
def context_summary(project_id: str):
    summary = read_json(project_dir(project_id) / "context_summary.json")
    if not summary:
        raise HTTPException(status_code=404, detail="Context summary not found")
    return summary


@router.get("/kb/summary")
def kb_summary(compressed: bool = False):
    try:
        return build_knowledge_base_summary(compressed=compressed)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/harness/run")
def run_harness(req: HarnessRunRequest):
    try:
        state = get_project(req.project_id)
        return run_timeline_harness(
            state,
            style_templates=req.style_templates or None,
            target_duration=req.target_duration,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/harness/preview-run")
def run_harness_preview(req: HarnessPreviewRequest):
    try:
        state = get_project(req.project_id)
        return run_preview_harness(
            state,
            style_templates=req.style_templates or None,
            target_duration=req.target_duration,
            render=req.render,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/harness/score")
def score_harness(req: HarnessScoreRequest):
    try:
        return save_harness_score(
            project_id=req.project_id,
            run_id=req.run_id,
            human_score=req.human_score,
            liked=req.liked,
            disliked=req.disliked,
            winner=req.winner,
            notes=req.notes,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/harness/promote")
def promote_harness(req: HarnessPromoteRequest):
    try:
        state = get_project(req.project_id)
        return promote_harness_run(
            state,
            run_id=req.run_id,
            target_duration=req.target_duration,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/harness/report/{project_id}")
def harness_report(project_id: str):
    report = read_json(project_dir(project_id) / "harness_report.json")
    if not report:
        raise HTTPException(status_code=404, detail="Harness report not found")
    return report


@router.get("/harness/preview/{project_id}/{filename}")
def harness_preview(project_id: str, filename: str):
    base = (project_asset_dir("outputs", project_id) / "harness_previews").resolve()
    path = (base / Path(filename).name).resolve()
    if base not in path.parents or not path.exists() or path.suffix.lower() != ".mp4":
        raise HTTPException(status_code=404, detail="Preview not found")
    return FileResponse(path, media_type="video/mp4")


@router.post("/critic/run")
def run_edit_critic(req: CriticRequest):
    try:
        state = get_project(req.project_id)
        return critique_project_edit(state)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/critic/revise")
def revise_from_critic(req: CriticRequest):
    try:
        state = get_project(req.project_id)
        report = critique_project_edit(state)
        result = revise_timeline_from_critic(state, report)
        if req.apply_revision:
            state.timeline = result["timeline"]
            state.status = "timeline_revised"
            state.progress = max(state.progress, 84)
            save_project(state)
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/frames/analyze")
def analyze_frames(req: FrameAnalyzeRequest):
    try:
        return analyze_frame_directory(
            frame_dir=req.frame_dir,
            project_id=req.project_id,
            sample_limit=req.sample_limit,
            use_ai=req.use_ai,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
