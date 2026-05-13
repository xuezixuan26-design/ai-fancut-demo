from pathlib import Path
import tempfile

from app.config import settings
from app.services.subtitle_renderer import write_ass_subtitles
from app.utils.ffmpeg_utils import ffmpeg_escape_path, require_ffmpeg, run_ffmpeg


def _moviepy_imports():
    try:
        from moviepy.editor import VideoFileClip, concatenate_videoclips, AudioFileClip, ColorClip, CompositeVideoClip
        import moviepy.video.fx.all as vfx
    except Exception as exc:
        raise RuntimeError(f"MoviePy import failed: {exc}") from exc
    return VideoFileClip, concatenate_videoclips, AudioFileClip, ColorClip, CompositeVideoClip, vfx


def _crop_9x16(clip):
    w, h = clip.size
    target_ratio = 9 / 16
    current_ratio = w / h
    if current_ratio > target_ratio:
        new_w = int(h * target_ratio)
        return clip.crop(x_center=w / 2, width=new_w, height=h)
    new_h = int(w / target_ratio)
    return clip.crop(y_center=h / 2, width=w, height=new_h)


def _apply_zoom(clip, effect: str):
    if effect not in {"slow_zoom_in", "slight_zoom", "soft_glow"}:
        return clip
    intensity = 0.08 if effect == "slow_zoom_in" else 0.035
    duration = max(0.1, clip.duration)
    zoomed = clip.resize(lambda t: 1 + intensity * min(1, t / duration))
    return zoomed.crop(
        x_center=zoomed.w / 2,
        y_center=zoomed.h / 2,
        width=settings.output_width,
        height=settings.output_height,
    )


def _flash_clip(duration: float = 0.08):
    _, _, _, ColorClip, _, _ = _moviepy_imports()
    return ColorClip(size=(settings.output_width, settings.output_height), color=(255, 255, 255), duration=duration).set_fps(settings.output_fps)


def render_video(project_id: str, timeline: dict, source_dir: Path, bgm_path: Path | None, output_path: Path, keep_original_audio: bool = False) -> Path:
    require_ffmpeg()
    VideoFileClip, concatenate_videoclips, AudioFileClip, _, _, vfx = _moviepy_imports()
    clips = []

    for item in timeline.get("timeline", []):
        source_path = source_dir / item["source"]
        if not source_path.exists():
            continue
        base = VideoFileClip(str(source_path)).subclip(float(item["start"]), float(item["end"]))
        speed = max(0.2, float(item.get("speed", 1.0)))
        if speed != 1.0:
            base = base.fx(vfx.speedx, factor=speed)
        base = _crop_9x16(base).resize((settings.output_width, settings.output_height)).set_fps(settings.output_fps)
        base = _apply_zoom(base, item.get("effect", "slight_zoom"))
        if not keep_original_audio:
            base = base.without_audio()
        if item.get("transition") == "flash_white" and clips:
            clips.append(_flash_clip())
        clips.append(base)

    if not clips:
        raise RuntimeError("No renderable clips in timeline.")

    final = concatenate_videoclips(clips, method="compose")
    target_duration = min(float(timeline.get("target_duration", final.duration)), final.duration)
    final = final.subclip(0, target_duration)
    if bgm_path and bgm_path.exists():
        bgm_audio = AudioFileClip(str(bgm_path))
        audio = bgm_audio.subclip(0, min(target_duration, bgm_audio.duration)).volumex(0.95)
        final = final.set_audio(audio)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        temp_video = Path(tmp) / "no_subtitles.mp4"
        ass_path = Path(tmp) / "captions.ass"
        final.write_videofile(
            str(temp_video),
            fps=settings.output_fps,
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            threads=4,
            logger=None,
        )
        write_ass_subtitles(timeline, ass_path, settings.output_width, settings.output_height)
        color_grade = timeline.get("color_grade", "cool_white_soft")
        grade_filter = {
            "cool_white_soft": "eq=contrast=1.06:brightness=0.025:saturation=0.92,colorbalance=bs=0.05:rs=-0.02",
            "warm_soft": "eq=contrast=1.04:brightness=0.02:saturation=1.08,colorbalance=rs=0.04:bs=-0.03",
            "cinematic_low_saturation": "eq=contrast=1.12:brightness=-0.01:saturation=0.78",
        }.get(color_grade, "eq=contrast=1.04:brightness=0.01:saturation=0.95")
        filters = f"{grade_filter},subtitles='{ffmpeg_escape_path(ass_path)}'"
        run_ffmpeg(
            [
                "-i",
                str(temp_video),
                "-vf",
                filters,
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-r",
                str(settings.output_fps),
                "-c:a",
                "aac",
                "-shortest",
                str(output_path),
            ]
        )
    final.close()
    for clip in clips:
        try:
            clip.close()
        except Exception:
            pass
    return output_path
