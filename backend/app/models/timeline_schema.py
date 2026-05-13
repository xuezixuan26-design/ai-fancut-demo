from pydantic import BaseModel, Field


class TimelineItem(BaseModel):
    source: str
    start: float
    end: float
    speed: float = 1.0
    effect: str = "slight_zoom"
    transition: str = "hard_cut"
    caption: str = ""
    beat_align: bool = True


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
    timeline: list[TimelineItem] = Field(default_factory=list)
    ending: Ending = Field(default_factory=Ending)
