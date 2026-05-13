from pydantic import BaseModel, Field


class ProjectState(BaseModel):
    project_id: str
    videos: list[str] = Field(default_factory=list)
    bgm: str | None = None
    reference: str | None = None
    reference_style: dict | None = None
    frame_analysis: list[dict] = Field(default_factory=list)
    candidate_clips: list[dict] = Field(default_factory=list)
    beats: dict | None = None
    timeline: dict | None = None
    output: str | None = None
    status: str = "created"
    progress: int = 0


class ProjectRequest(BaseModel):
    project_id: str


class TimelineRequest(BaseModel):
    project_id: str
    style_template: str = "korean_cool_white"
    target_duration: int = 30
    use_llm: bool = True


class RenderRequest(BaseModel):
    project_id: str
    keep_original_audio: bool = False
