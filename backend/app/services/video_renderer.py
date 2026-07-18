from pathlib import Path
import tempfile

from app.config import settings
from app.services.aspect_ratio import output_size
from app.services.duration_policy import timeline_target_duration
from app.utils.ffmpeg_utils import require_ffmpeg, run_ffmpeg


def render_video(
    project_id: str,
    timeline: dict,
    source_dir: Path,
    bgm_path: Path | None,
    output_path: Path,
    keep_original_audio: bool = False,
) -> Path:
    """Render with FFmpeg segment-by-segment to avoid MoviePy memory spikes."""
    _ = project_id
    require_ffmpeg()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    render_items = _renderable_items(timeline, source_dir)
    if not render_items:
        raise RuntimeError("No renderable clips in timeline.")

    with tempfile.TemporaryDirectory(prefix="fancut_render_") as tmp_name:
        tmp_dir = Path(tmp_name)
        segments: list[Path] = []
        skipped: list[dict] = []
        for index, item in enumerate(render_items):
            transition = item.get("transition")
            if transition and transition != "hard_cut" and segments:
                transition_path = tmp_dir / f"segment_{len(segments):04d}_{transition}.mp4"
                try:
                    _render_transition_segment(transition_path, transition, timeline)
                    segments.append(transition_path)
                except Exception as exc:
                    skipped.append({"index": index, "source": item.get("source"), "stage": "transition", "error": str(exc)})

            segment_path = tmp_dir / f"segment_{len(segments):04d}.mp4"
            try:
                _render_timeline_segment(item, source_dir / item["source"], segment_path)
                segments.append(segment_path)
            except Exception as exc:
                skipped.append({"index": index, "source": item.get("source"), "stage": "clip", "error": str(exc)})

        if not segments:
            raise RuntimeError(f"No segments rendered successfully. Skipped: {skipped[:3]}")
        if skipped:
            timeline["render_warnings"] = skipped[:12]

        joined_path = tmp_dir / "joined.mp4"
        _concat_segments(segments, joined_path, tmp_dir / "concat.txt")
        _finalize_video(joined_path, timeline, bgm_path, output_path, keep_original_audio)

    return output_path


def _renderable_items(timeline: dict, source_dir: Path) -> list[dict]:
    items: list[dict] = []
    for item in timeline.get("timeline", []):
        source = item.get("source")
        if not source:
            continue
        source_path = source_dir / source
        if not source_path.exists():
            continue
        try:
            start = max(0.0, float(item.get("start", 0)))
            end = max(start + 0.05, float(item.get("end", start + 0.05)))
        except (TypeError, ValueError):
            continue
        copied = dict(item)
        copied["start"] = start
        copied["end"] = end
        copied["aspect_ratio"] = timeline.get("aspect_ratio", "9:16")
        items.append(copied)
    return items


def _timeline_output_size(timeline: dict) -> tuple[int, int]:
    return output_size(timeline.get("aspect_ratio"))


def _item_output_size(item: dict) -> tuple[int, int]:
    return output_size(item.get("aspect_ratio"))


def _render_timeline_segment(item: dict, source_path: Path, output_path: Path) -> None:
    start = float(item["start"])
    source_duration = max(0.05, float(item["end"]) - start)
    speed = max(0.2, min(4.0, float(item.get("speed", 1.0) or 1.0)))
    output_duration = max(0.05, source_duration / speed)
    filters = _segment_filters(item, speed, output_duration)

    args = [
        "-ss",
        f"{start:.3f}",
        "-t",
        f"{source_duration:.3f}",
        "-i",
        str(source_path),
        "-vf",
        filters,
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-crf",
        "16",
        "-threads",
        "1",
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(settings.output_fps),
        "-t",
        f"{output_duration:.3f}",
        str(output_path),
    ]
    run_ffmpeg(args, timeout=_segment_timeout(source_path, output_duration))


def _segment_timeout(source_path: Path, output_duration: float) -> int:
    suffix = source_path.suffix.lower()
    base = 70 if suffix in {".mp4", ".mov", ".m4v"} else 50
    return max(base, int(40 + output_duration * 28))


def _segment_filters(item: dict, speed: float, output_duration: float) -> str:
    width, height = _item_output_size(item)
    filters = [_fit_preserve_subject_filter(item, width, height)]
    effect = item.get("effect", "slight_zoom")
    filters.append(_motion_filter(str(effect), output_duration, width, height))
    if effect == "soft_glow":
        filters.append("eq=contrast=1.03:brightness=0.018:saturation=1.03")
    elif effect == "mono_mystery":
        filters.append("hue=s=0,eq=contrast=1.22:brightness=-0.025:saturation=0")
        filters.append("boxblur=1:1")
        filters.append("noise=alls=6:allf=t")
    elif effect == "soft_blur_reveal":
        filters.append("hue=s=0.18,eq=contrast=1.12:brightness=0.005:saturation=0.35")
        filters.append("boxblur=0.6:0.6")
    elif effect == "clarity_rise":
        filters.append("eq=contrast=1.12:brightness=0.028:saturation=0.82")
        filters.append("unsharp=5:5:0.35:3:3:0.12")
    elif effect == "desaturate_to_color":
        filters.append("eq=contrast=1.1:brightness=0.024:saturation=0.72,colorbalance=bs=0.03")
    elif effect in {"cool_white_face_glow", "breathing_zoom"}:
        filters.append("eq=contrast=1.08:brightness=0.035:saturation=0.92,colorbalance=bs=0.05:rs=-0.015")
        filters.append("unsharp=5:5:0.28:3:3:0.12")
    elif effect == "slow_motion_glow":
        filters.append("eq=contrast=1.07:brightness=0.038:saturation=0.95,colorbalance=bs=0.045:rs=-0.012")
        filters.append("unsharp=5:5:0.24:3:3:0.1")
        filters.append("boxblur=0.35:0.35")
    elif effect == "slowmo_beat_freeze":
        filters.append("eq=contrast=1.12:brightness=0.034:saturation=1.02,colorbalance=bs=0.035")
        filters.append("unsharp=7:7:0.48:3:3:0.18")
    elif effect == "hair_rim_light":
        filters.append("eq=contrast=1.1:brightness=0.026:saturation=0.95,colorbalance=bs=0.04")
        filters.append("unsharp=7:7:0.45:3:3:0.16")
    elif effect == "beauty_freeze":
        filters.append("eq=contrast=1.09:brightness=0.038:saturation=0.94,colorbalance=bs=0.04")
        filters.append("unsharp=5:5:0.34:3:3:0.12")
    elif effect == "zoom_punch":
        filters.append("eq=contrast=1.08:brightness=0.012:saturation=1.02")
    elif effect in {"snap_zoom", "beat_shake", "whip_push"}:
        filters.append("eq=contrast=1.1:brightness=0.012:saturation=1.04")
        filters.append("unsharp=5:5:0.45:3:3:0.2")
    elif effect in {"pan_left", "pan_right", "tilt_up", "tilt_down", "drift_zoom"}:
        filters.append("eq=contrast=1.045:brightness=0.012:saturation=1.02")
    elif effect in {"slow_zoom_in", "slight_zoom"}:
        filters.append("eq=contrast=1.04:brightness=0.01:saturation=1.01")
    else:
        filters.append("eq=contrast=1.02:brightness=0.006:saturation=1.0")
    if speed != 1.0:
        filters.append(f"setpts=PTS/{speed:.4f}")
    filters.append(f"fps={settings.output_fps}")
    filters.append("format=yuv420p")
    return ",".join(filters)


def _fit_preserve_subject_filter(item: dict, width: int, height: int) -> str:
    cx, cy = _crop_center(item)
    y_anchor = _face_y_anchor(item)
    x = f"min(max(iw*{cx:.4f}-ow*0.5\\,0)\\,iw-ow)"
    y = f"min(max(ih*{cy:.4f}-oh*{y_anchor:.4f}\\,0)\\,ih-oh)"
    return (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height}:{x}:{y}"
    )


def _crop_center(item: dict) -> tuple[float, float]:
    raw = item.get("crop_center") or [0.5, 0.42]
    try:
        cx = float(raw[0])
        cy = float(raw[1])
    except (TypeError, ValueError, IndexError):
        cx, cy = 0.5, 0.42
    return (min(0.78, max(0.22, cx)), min(0.82, max(0.16, cy)))


def _face_y_anchor(item: dict) -> float:
    shot_size = item.get("shot_size")
    if shot_size in {"closeup", "medium_closeup"}:
        return 0.4
    if shot_size == "half_body":
        return 0.32
    if shot_size == "full_body":
        return 0.24
    return 0.34


def _motion_filter(effect: str, duration: float, width: int, height: int) -> str:
    frames = max(1.0, duration * settings.output_fps)
    p = f"n/{frames:.3f}"

    zoom = "1.035"
    x = "(iw-ow)/2"
    y = "(ih-oh)/2"
    if effect == "slow_zoom_in":
        zoom = f"1+0.08*{p}"
    elif effect in {"micro_push", "mono_mystery", "soft_blur_reveal", "clarity_rise", "desaturate_to_color", "cool_white_face_glow", "hair_rim_light", "beauty_freeze"}:
        zoom = f"1.01+0.035*{p}"
    elif effect == "slow_motion_glow":
        zoom = f"1.015+0.035*{p}"
    elif effect == "slowmo_beat_freeze":
        zoom = f"1.035+0.075*sin(PI*{p})"
    elif effect == "breathing_zoom":
        zoom = f"1.025+0.012*sin(2*PI*{p})+0.02*{p}"
    elif effect == "slight_zoom":
        zoom = f"1.025+0.018*{p}"
    elif effect == "soft_glow":
        zoom = f"1.035+0.02*{p}"
    elif effect == "drift_zoom":
        zoom = f"1.04+0.045*{p}"
        x = f"(iw-ow)/2+(iw-ow)*0.12*({p}-0.5)"
        y = f"(ih-oh)/2-(ih-oh)*0.08*({p}-0.5)"
    elif effect == "pan_left":
        zoom = "1.085"
        x = f"(iw-ow)/2+(iw-ow)*0.18*(0.5-{p})"
    elif effect == "pan_right":
        zoom = "1.085"
        x = f"(iw-ow)/2+(iw-ow)*0.18*({p}-0.5)"
    elif effect == "tilt_up":
        zoom = "1.075"
        y = f"(ih-oh)/2+(ih-oh)*0.16*(0.5-{p})"
    elif effect == "tilt_down":
        zoom = "1.075"
        y = f"(ih-oh)/2+(ih-oh)*0.16*({p}-0.5)"
    elif effect == "zoom_punch":
        zoom = f"1.04+0.10*sin(PI*{p})"
    elif effect == "snap_zoom":
        zoom = f"1.02+0.14*sin(PI*{p})"
    elif effect == "beat_shake":
        zoom = "1.09"
        x = "(iw-ow)/2+sin(n*1.7)*12"
        y = "(ih-oh)/2+cos(n*1.3)*8"
    elif effect == "whip_push":
        zoom = "1.14"
        x = f"(iw-ow)/2+(iw-ow)*0.38*(0.5-{p})"

    return f"scale=trunc(iw*({zoom})/2)*2:trunc(ih*({zoom})/2)*2:eval=frame,crop={width}:{height}:{x}:{y}"


def _render_transition_segment(output_path: Path, transition: str, timeline: dict) -> None:
    transition_map = {
        "flash_white": ("white", 0.14, "flash"),
        "flash_black": ("black", 0.16, "fade"),
        "glow_flash": ("0xf8fbff", 0.2, "glow"),
        "strobe_white": ("white", 0.12, "strobe"),
        "whip_flash": ("0xeeeeee", 0.16, "whip"),
        "crossfade": ("0xf3f6f7", 0.22, "fade"),
        "soft_wash": ("0xf7fbff", 0.26, "glow"),
        "bloom_blur": ("0xfaf7ff", 0.24, "bloom"),
        "whip_pan": ("0xeceff2", 0.2, "whip"),
        "luma_fade": ("0x111111", 0.22, "fade"),
        "zoom_burst": ("0xf8fbff", 0.24, "zoom"),
        "spin_blur": ("0xf5f0ff", 0.28, "spin"),
        "rotate_flash": ("0xffffff", 0.22, "rotate"),
        "shake_zoom": ("0xf2f5f7", 0.22, "shake_zoom"),
    }
    color, duration, mode = transition_map.get(transition, ("white", 0.18, "fade"))
    _render_flash_segment(output_path, timeline, color=color, duration=duration, mode=mode)


def _render_flash_segment(output_path: Path, timeline: dict, color: str = "white", duration: float = 0.18, mode: str = "fade") -> None:
    width, height = _timeline_output_size(timeline)
    filters = _transition_filter(mode, duration, width, height)
    run_ffmpeg(
        [
            "-f",
            "lavfi",
            "-i",
            f"color=c={color}:s={width}x{height}:r={settings.output_fps}:d={duration}",
            "-vf",
            filters,
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "16",
            "-threads",
            "1",
            "-pix_fmt",
            "yuv420p",
            str(output_path),
        ],
        timeout=20,
    )


def _transition_filter(mode: str, duration: float, width: int, height: int) -> str:
    fade_out_start = max(0.01, duration * 0.58)
    filters = []
    if mode == "strobe":
        filters.append("tblend=all_mode=lighten")
        filters.append("eq=contrast=1.25:brightness=0.04:saturation=0.9")
        filters.append(_transition_texture())
    elif mode == "whip":
        filters.append("noise=alls=9:allf=t")
        filters.append(_transition_texture())
        filters.append("boxblur=3:1")
        filters.append(_zoom_crop_expr(width, height, zoom_expr=f"1.08+0.18*sin(PI*t/{duration:.3f})", x_expr="(iw-ow)/2+sin(t*46)*34", y_expr="(ih-oh)/2"))
        filters.append("eq=contrast=1.18:brightness=0.025:saturation=0.85")
    elif mode == "bloom":
        filters.append(_transition_texture())
        filters.append("boxblur=8:2")
        filters.append(_zoom_crop_expr(width, height, zoom_expr=f"1.02+0.16*sin(PI*t/{duration:.3f})"))
        filters.append("eq=contrast=1.08:brightness=0.08:saturation=1.05")
        filters.append("noise=alls=4:allf=t")
    elif mode == "zoom":
        filters.append(_transition_texture())
        filters.append("noise=alls=7:allf=t")
        filters.append(_zoom_crop_expr(width, height, zoom_expr=f"1.02+0.34*sin(PI*t/{duration:.3f})"))
        filters.append("eq=contrast=1.18:brightness=0.07:saturation=0.92")
    elif mode == "spin":
        filters.append(_transition_texture())
        filters.append("noise=alls=8:allf=t")
        filters.append(f"rotate=0.42*sin(PI*t/{duration:.3f}):fillcolor=black@0.0")
        filters.append(_zoom_crop_expr(width, height, zoom_expr=f"1.16+0.18*sin(PI*t/{duration:.3f})"))
        filters.append("boxblur=2:1")
        filters.append("eq=contrast=1.16:brightness=0.055:saturation=0.9")
    elif mode == "rotate":
        filters.append(_transition_texture())
        filters.append(f"rotate=0.22*sin(2*PI*t/{duration:.3f}):fillcolor=white@0.0")
        filters.append(_zoom_crop_expr(width, height, zoom_expr=f"1.06+0.2*sin(PI*t/{duration:.3f})"))
        filters.append("eq=contrast=1.2:brightness=0.07:saturation=0.88")
    elif mode == "shake_zoom":
        filters.append(_transition_texture())
        filters.append("noise=alls=10:allf=t")
        filters.append(_zoom_crop_expr(width, height, zoom_expr=f"1.12+0.24*sin(PI*t/{duration:.3f})", x_expr="(iw-ow)/2+sin(t*80)*22", y_expr="(ih-oh)/2+cos(t*67)*18"))
        filters.append("eq=contrast=1.22:brightness=0.045:saturation=0.86")
    elif mode == "glow":
        filters.append(_transition_texture())
        filters.append("boxblur=4:1")
        filters.append("eq=contrast=1.04:brightness=0.065:saturation=0.95")
    elif mode == "flash":
        filters.append(_transition_texture())
        filters.append("eq=contrast=1.22:brightness=0.05:saturation=0.85")
    else:
        filters.append(_transition_texture())
        filters.append("eq=contrast=1.02:brightness=0.01:saturation=0.9")
    filters.append(f"fade=t=in:st=0:d={duration * 0.35:.3f}")
    filters.append(f"fade=t=out:st={fade_out_start:.3f}:d={duration * 0.38:.3f}")
    filters.append("format=yuv420p")
    return ",".join(filters)


def _transition_texture() -> str:
    return "drawgrid=width=135:height=135:thickness=2:color=white@0.16"


def _zoom_crop_expr(
    width: int,
    height: int,
    zoom_expr: str,
    x_expr: str = "(iw-ow)/2",
    y_expr: str = "(ih-oh)/2",
) -> str:
    return f"scale=trunc(iw*({zoom_expr})/2)*2:trunc(ih*({zoom_expr})/2)*2:eval=frame,crop={width}:{height}:{x_expr}:{y_expr}"


def _concat_segments(segments: list[Path], output_path: Path, list_path: Path) -> None:
    list_path.write_text(
        "".join(f"file '{_concat_path(segment)}'\n" for segment in segments),
        encoding="utf-8",
    )
    run_ffmpeg(
        [
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_path),
            "-c",
            "copy",
            str(output_path),
        ],
        timeout=max(90, len(segments) * 4),
    )


def _finalize_video(
    joined_path: Path,
    timeline: dict,
    bgm_path: Path | None,
    output_path: Path,
    keep_original_audio: bool,
) -> None:
    target_duration = timeline_target_duration(timeline)
    width, height = _timeline_output_size(timeline)
    pad_filter = f",tpad=stop_mode=clone:stop_duration={target_duration:.3f}" if target_duration else ""
    grade_filter = f"{_grade_filter(timeline)}{pad_filter},scale={width}:{height}:flags=lanczos,format=yuv420p"
    args = ["-i", str(joined_path)]
    if bgm_path and bgm_path.exists():
        args.extend(["-stream_loop", "-1", "-i", str(bgm_path)])

    args.extend(
        [
            "-vf",
            grade_filter,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "14",
            "-threads",
            "1",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(settings.output_fps),
        ]
    )
    if target_duration:
        args.extend(["-t", f"{target_duration:.3f}"])

    if bgm_path and bgm_path.exists():
        args.extend(["-map", "0:v:0", "-map", "1:a:0", "-c:a", "aac", "-b:a", "192k"])
    elif keep_original_audio:
        args.extend(["-an"])
    else:
        args.extend(["-an"])

    args.extend(["-movflags", "+faststart", str(output_path)])
    item_count = len(timeline.get("timeline", []) or [])
    timeout = max(180, int((target_duration or 30) * 12 + item_count * 4))
    run_ffmpeg(args, timeout=timeout)


def _concat_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace("'", "'\\''")


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
        if effect in {"red_black_stage_grade", "cool_white_soft_grade", "balanced_beauty_grade", "cool_white_face_glow"}:
            track_grade = effect
            break
    color_grade = timeline.get("color_grade", "cool_white_soft")
    grade_filter = {
        "cool_white_soft": "eq=contrast=1.06:brightness=0.025:saturation=0.92,colorbalance=bs=0.05:rs=-0.02",
        "warm_soft": "eq=contrast=1.04:brightness=0.02:saturation=1.08,colorbalance=rs=0.04:bs=-0.03",
        "cinematic_low_saturation": "eq=contrast=1.12:brightness=-0.01:saturation=0.78",
        "red_black_stage_grade": "eq=contrast=1.15:brightness=0.005:saturation=1.12,colorbalance=rs=0.05:bs=-0.03",
        "cool_white_soft_grade": "eq=contrast=1.07:brightness=0.028:saturation=0.9,colorbalance=bs=0.06:rs=-0.02",
        "cool_white_face_glow": "eq=contrast=1.08:brightness=0.034:saturation=0.9,colorbalance=bs=0.055:rs=-0.018",
        "balanced_beauty_grade": "eq=contrast=1.04:brightness=0.01:saturation=0.98",
    }
    return grade_filter.get(track_grade or color_grade, "eq=contrast=1.04:brightness=0.01:saturation=0.95")
