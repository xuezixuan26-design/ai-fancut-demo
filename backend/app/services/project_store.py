from app.models.schemas import ProjectState
from app.utils.file_utils import new_project_id, project_asset_dir, project_dir
from app.config import settings
from app.utils.json_utils import read_json, write_json
from app.services.render_history import load_render_history


def create_project() -> ProjectState:
    state = ProjectState(project_id=new_project_id())
    save_project(state)
    return state


def get_project(project_id: str) -> ProjectState:
    path = project_dir(project_id) / "project.json"
    data = read_json(path)
    if not data:
        raise FileNotFoundError(f"Project not found: {project_id}")
    state = ProjectState(**data)
    return reconcile_project_outputs(state)


def save_project(state: ProjectState) -> None:
    write_json(project_dir(state.project_id) / "project.json", state.model_dump())


def reconcile_project_outputs(state: ProjectState) -> ProjectState:
    output_dir = project_asset_dir("outputs", state.project_id)
    raw_dir = project_asset_dir("raw_videos", state.project_id)
    output_path = output_dir / "output.mp4"
    enhanced_path = output_dir / "enhanced_output.mp4"
    changed = False

    if raw_dir.exists():
        raw_names = sorted(
            path.name
            for path in raw_dir.iterdir()
            if path.is_file() and path.suffix.lower() in {".mp4", ".mov", ".m4v"}
        )
        merged_videos = [name for name in state.videos if name in raw_names]
        merged_videos.extend(name for name in raw_names if name not in merged_videos)
        if merged_videos != state.videos:
            state.videos = merged_videos
            changed = True

    if output_path.exists() and not state.output:
        state.output = output_path.name
        if state.status == "rendering":
            state.status = "done"
            state.progress = 100
        changed = True

    if enhanced_path.exists() and not state.enhanced_output:
        state.enhanced_output = enhanced_path.name
        if state.status == "enhancing":
            state.status = "enhanced"
            state.progress = 100
        changed = True

    history = load_render_history(state.project_id)
    if history != state.render_history:
        state.render_history = history
        changed = True

    if changed:
        save_project(state)
    return state


def get_or_create_project(project_id: str | None = None) -> ProjectState:
    if project_id:
        return get_project(project_id)
    return create_project()


def get_latest_project() -> ProjectState:
    projects_dir = settings.storage_dir / "projects"
    project_files = sorted(
        projects_dir.glob("*/project.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for path in project_files:
        try:
            return get_project(path.parent.name)
        except Exception:
            continue
    raise FileNotFoundError("No project found")
