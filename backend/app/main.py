from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.api import analyze, engineering, render, timeline, upload
from app.config import settings
from app.services.project_store import create_project, get_latest_project, get_project
from app.utils.file_utils import ensure_storage

ensure_storage()

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix=settings.api_prefix)
app.include_router(analyze.router, prefix=settings.api_prefix)
app.include_router(timeline.router, prefix=settings.api_prefix)
app.include_router(render.router, prefix=settings.api_prefix)
app.include_router(engineering.router, prefix=settings.api_prefix)


@app.get("/health")
def health():
    return {"ok": True, "app": settings.app_name}


@app.get("/api/project/latest")
def latest_project():
    try:
        return get_latest_project().model_dump()
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/project")
def new_project():
    try:
        return create_project().model_dump()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/project/{project_id}")
def project(project_id: str):
    try:
        return get_project(project_id).model_dump()
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
