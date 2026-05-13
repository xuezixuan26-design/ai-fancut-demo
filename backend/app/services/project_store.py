from app.models.schemas import ProjectState
from app.utils.file_utils import new_project_id, project_dir
from app.utils.json_utils import read_json, write_json


def create_project() -> ProjectState:
    state = ProjectState(project_id=new_project_id())
    save_project(state)
    return state


def get_project(project_id: str) -> ProjectState:
    path = project_dir(project_id) / "project.json"
    data = read_json(path)
    if not data:
        raise FileNotFoundError(f"Project not found: {project_id}")
    return ProjectState(**data)


def save_project(state: ProjectState) -> None:
    write_json(project_dir(state.project_id) / "project.json", state.model_dump())


def get_or_create_project(project_id: str | None = None) -> ProjectState:
    if project_id:
        return get_project(project_id)
    return create_project()
