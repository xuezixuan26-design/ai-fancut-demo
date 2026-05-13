from pathlib import Path


def ass_timestamp(seconds: float) -> str:
    cs = int(round(seconds * 100))
    h = cs // 360000
    cs %= 360000
    m = cs // 6000
    cs %= 6000
    s = cs // 100
    cs %= 100
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def write_ass_subtitles(timeline: dict, ass_path: Path, width: int = 1080, height: int = 1920) -> None:
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {width}",
        f"PlayResY: {height}",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Fancut,Arial,72,&H00FFFFFF,&H00FFFFFF,&H00000000,&H66000000,-1,0,0,0,100,100,0,0,1,5,1,2,60,60,210,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    cursor = 0.0
    for item in timeline.get("timeline", []):
        raw_duration = max(0.1, float(item["end"]) - float(item["start"]))
        duration = raw_duration / max(0.2, float(item.get("speed", 1.0)))
        caption = (item.get("caption") or "").strip()
        if caption:
            lines.append(
                f"Dialogue: 0,{ass_timestamp(cursor)},{ass_timestamp(cursor + min(duration, 1.8))},Fancut,,0,0,0,,{caption}"
            )
        cursor += duration
    ending = timeline.get("ending") or {}
    if ending.get("caption"):
        lines.append(f"Dialogue: 0,{ass_timestamp(max(0, cursor - 1.8))},{ass_timestamp(cursor)},Fancut,,0,0,0,,{ending['caption']}")
    ass_path.parent.mkdir(parents=True, exist_ok=True)
    ass_path.write_text("\n".join(lines), encoding="utf-8")
