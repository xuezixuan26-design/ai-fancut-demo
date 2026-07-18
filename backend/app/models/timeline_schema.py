from pydantic import BaseModel, Field


class TimelineItem(BaseModel):
    source: str
    start: float
    end: float
    speed: float = 1.0
    effect: str = "slight_zoom"
    transition: str = "hard_cut"
    camera_instruction: dict = Field(default_factory=dict)
    transition_instruction: dict = Field(default_factory=dict)
    slow_motion: dict = Field(default_factory=dict)
    caption: str = ""
    beat_align: bool = True
    beat_hit: bool = False
    music_section: str = "unknown"
    output_start: float | None = None
    output_end: float | None = None
    visual_change_strength: float = 0.0
    role: str = "beat_cut"
    shot_size: str = "unknown"
    subject_position: str = "unknown"
    crop_center: tuple[float, float] | None = None


class AppliedSkill(BaseModel):
    skill_id: str
    skill_name: str
    type: str = "technical"
    confidence: float = 0.0
    reason: str = ""


class TrackItem(BaseModel):
    kind: str
    start: float = 0.0
    end: float = 0.0
    source: str | None = None
    effect: str | None = None
    params: dict = Field(default_factory=dict)


class TimelineTrack(BaseModel):
    track_id: str
    track_type: str
    label: str
    items: list[TrackItem] = Field(default_factory=list)


class Ending(BaseModel):
    effect: str = "freeze_frame"
    caption: str = "神颜名场面"


class TimelinePlan(BaseModel):
    title: str = "这一秒直接入坑"
    target_duration: float = 30
    aspect_ratio: str = "9:16"
    style: str = "颜值向饭圈卡点"
    color_grade: str = "cool_white_soft"
    caption_style: str = "bold_white_black_outline"
    applied_skills: list[AppliedSkill] = Field(default_factory=list)
    tracks: list[TimelineTrack] = Field(default_factory=list)
    timeline: list[TimelineItem] = Field(default_factory=list)
    ending: Ending = Field(default_factory=Ending)
