from pathlib import Path
import tempfile

from app.config import settings
from app.utils.ffmpeg_utils import require_ffmpeg, run_ffmpeg


def _moviepy_imports():
    try:
        from moviepy.editor import AudioFileClip, ColorClip, CompositeVideoClip, VideoFileClip, concatenate_videoclips
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
    if effect not in {"slow_zoom_in", "slight_zoom", "soft_glow", "zoom_punch"}:
        return clip
    intensity = {
        "slow_zoom_in": 0.08,
        "slight_zoom": 0.035,
        "soft_glow": 0.025,
        "zoom_punch": 0.12,
    }.get(effect, 0.035)
    duration = max(0.1, clip.duration)
    if effect == "zoom_punch":
        zoomed = clip.resize(lambda t: 1 + intensity * max(0, 1 - abs((t / duration) - 0.35) * 2.8))
    else:
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
        if item.get("effect") == "soft_glow":
            base = base.fx(vfx.colorx, 1.04)
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
    final = _apply_track_overlays(final, timeline)
    if bgm_path and bgm_path.exists():
        bgm_audio = AudioFileClip(str(bgm_path))
        audio = bgm_audio.subclip(0, min(final.duration, bgm_audio.duration)).volumex(0.95)
        final = final.set_audio(audio)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        temp_video = Path(tmp) / "render_source.mp4"
        final.write_videofile(
            str(temp_video),
            fps=settings.output_fps,
            codec="libx264",
            audio_codec="aac",
            preset="slow",
            bitrate=None,
            audio_bitrate="192k",
            ffmpeg_params=["-crf", "16", "-pix_fmt", "yuv420p"],
            threads=4,
            logger=None,
        )
        grade_filter = _grade_filter(timeline)
        run_ffmpeg(
            [
                "-i",
                str(temp_video),
                "-vf",
                grade_filter,
                "-c:v",
                "libx264",
                "-preset",
                "slow",
                "-crf",
                "18",
                "-pix_fmt",
                "yuv420p",
                "-r",
                str(settings.output_fps),
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-movflags",
                "+faststart",
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


def _apply_track_overlays(final, timeline: dict):
    _, _, _, ColorClip, CompositeVideoClip, vfx = _moviepy_imports()
    overlays = []
    for item in _effect_items(timeline):
        start = max(0.0, float(item.get("start", 0)))
        end = min(float(item.get("end", start)), final.duration)
        duration = max(0.01, end - start)
        effect = item.get("effect")
        params = item.get("params", {})
        if effect == "flash_white":
            opacity = float(params.get("strength", 0.65))
            overlays.append(
                ColorClip((settings.output_width, settings.output_height), color=(255, 255, 255), duration=duration)
                .set_start(start)
                .set_opacity(opacity)
                .set_fps(settings.output_fps)
            )
        elif effect == "black_mask_reveal":
            mask = ColorClip((settings.output_width, settings.output_height), color=(0, 0, 0), duration=duration)
            mask = mask.set_opacity(0.75).fx(vfx.fadeout, min(duration, 0.9))
            overlays.append(mask.set_start(start).set_fps(settings.output_fps))
        elif effect == "face_focus_glow":
            overlays.append(
                ColorClip((settings.output_width, settings.output_height), color=(255, 255, 255), duration=duration)
                .set_start(start)
                .set_opacity(0.08)
                .set_fps(settings.output_fps)
            )
        elif effect == "ending_freeze_soft_glow":
            final = _append_ending_freeze(final, duration)
    if overlays:
        return CompositeVideoClip([final, *overlays], size=(settings.output_width, settings.output_height)).set_duration(final.duration)
    return final


def _append_ending_freeze(final, duration: float):
    if final.duration <= 0.2 or duration <= 0.05:
        return final
    _, concatenate_videoclips, _, _, _, vfx = _moviepy_imports()
    still = final.to_ImageClip(t=max(0, final.duration - 0.08)).set_duration(min(duration, 1.0))
    still = still.fx(vfx.fadeout, min(0.4, still.duration / 2))
    base = final.subclip(0, max(0.1, final.duration - still.duration))
    return concatenate_videoclips([base, still], method="compose")


def _effect_items(timeline: dict) -> list[dict]:
    items: list[dict] = []
    for track in timeline.get("tracks", []):
        if track.get("track_type") in {"effect", "overlay"}:
            items.extend(track.get("items", []))
    return items


def _grade_filter(timeline: dict) -> str:
    track_grade = None
    for item in _effect_items(timeline):
        effect = item.get("effect")
        if effect in {"red_black_stage_grade", "cool_white_soft_grade", "balanced_beauty_grade"}:
            track_grade = effect
            break
    color_grade = timeline.get("color_grade", "cool_white_soft")
    grade_filter = {
        "cool_white_soft": "eq=contrast=1.06:brightness=0.025:saturation=0.92,colorbalance=bs=0.05:rs=-0.02",
        "warm_soft": "eq=contrast=1.04:brightness=0.02:saturation=1.08,colorbalance=rs=0.04:bs=-0.03",
        "cinematic_low_saturation": "eq=contrast=1.12:brightness=-0.01:saturation=0.78",
        "red_black_stage_grade": "eq=contrast=1.15:brightness=0.005:saturation=1.12,colorbalance=rs=0.05:bs=-0.03",
        "cool_white_soft_grade": "eq=contrast=1.07:brightness=0.028:saturation=0.9,colorbalance=bs=0.06:rs=-0.02",
        "balanced_beauty_grade": "eq=contrast=1.04:brightness=0.01:saturation=0.98",
    }
    return grade_filter.get(track_grade or color_grade, "eq=contrast=1.04:brightness=0.01:saturation=0.95")
