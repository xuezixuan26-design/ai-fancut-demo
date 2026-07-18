from pydantic import BaseModel, Field


class ProjectState(BaseModel):
    project_id: str
    aspect_ratio: str = "9:16"
    videos: list[str] = Field(default_factory=list)
    bgm: str | None = None
    reference: str | None = None
    reference_style: dict | None = None
    frame_analysis: list[dict] = Field(default_factory=list)
    candidate_clips: list[dict] = Field(default_factory=list)
    beats: dict | None = None
    timeline: dict | None = None
    output: str | None = None
    enhanced_output: str | None = None
    render_history: list[dict] = Field(default_factory=list)
    status: str = "created"
    progress: int = 0


class ProjectRequest(BaseModel):
    project_id: str


class TimelineRequest(BaseModel):
    project_id: str
    style_template: str = "korean_cool_white"
    aspect_ratio: str = "9:16"
    target_duration: int | None = None
    use_llm: bool = True


class RenderRequest(BaseModel):
    project_id: str
    keep_original_audio: bool = False
    cleanup_sources: bool = True
    archive_history: bool = True


class EnhanceRequest(BaseModel):
    project_id: str
    mode: str = "ffmpeg_hq"
    preset: str = "idol_stage_hq"


class ContextCompressRequest(BaseModel):
    project_id: str
    feedback: str | None = None


class HarnessRunRequest(BaseModel):
    project_id: str
    style_templates: list[str] = Field(default_factory=list)
    target_duration: int | None = None


class HarnessPreviewRequest(BaseModel):
    project_id: str
    style_templates: list[str] = Field(default_factory=list)
    target_duration: int = 12
    render: bool = True


class HarnessScoreRequest(BaseModel):
    project_id: str
    run_id: str
    human_score: float | None = None
    liked: list[str] = Field(default_factory=list)
    disliked: list[str] = Field(default_factory=list)
    winner: bool = False
    notes: str = ""


class HarnessPromoteRequest(BaseModel):
    project_id: str
    run_id: str | None = None
    target_duration: int | None = None


class FrameAnalyzeRequest(BaseModel):
    frame_dir: str
    project_id: str | None = None
    sample_limit: int = 12
    use_ai: bool = False


class CriticRequest(BaseModel):
    project_id: str
    apply_revision: bool = True
    render_after: bool = False
