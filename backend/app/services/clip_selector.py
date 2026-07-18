from collections import Counter, defaultdict


def select_candidate_clips(frame_rows: list[dict], max_per_video: int = 16) -> list[dict]:
    by_video: dict[str, list[dict]] = defaultdict(list)
    for row in frame_rows:
        by_video[row["video"]].append(row)

    selected: list[dict] = []
    for video, rows in by_video.items():
        rows = sorted(rows, key=lambda r: r["timestamp"])
        candidates = _strict_candidates_for_video(video, rows)
        if not candidates:
            candidates = _fallback_candidates_for_video(video, rows, limit=min(8, max_per_video))
        selected.extend(sorted(candidates, key=lambda c: c["highlight_score"], reverse=True)[:max_per_video])

    return _interleave_by_source(selected)


def _strict_candidates_for_video(video: str, rows: list[dict]) -> list[dict]:
    groups: list[list[dict]] = []
    current: list[dict] = []
    for row in rows:
        valid = (
            row["face_detected"]
            and row["highlight_score"] >= 5.6
            and 45 <= row["brightness"] <= 220
            and row["sharpness_score"] >= 2.2
        )
        if valid:
            current.append(row)
        elif current:
            groups.append(current)
            current = []
    if current:
        groups.append(current)

    candidates: list[dict] = []
    for group in groups:
        start = max(0.0, group[0]["timestamp"] - 0.2)
        end = group[-1]["timestamp"] + 0.8
        duration = end - start
        if duration < 0.8:
            end = start + 0.8
            duration = 0.8
        if duration > 3.0:
            best = max(group, key=lambda r: r["highlight_score"])
            start = max(0.0, best["timestamp"] - 0.6)
            end = start + 1.6
            duration = 1.6
        candidates.append(_candidate_from_group(video, start, end, duration, group))
    return candidates


def _fallback_candidates_for_video(video: str, rows: list[dict], limit: int) -> list[dict]:
    usable_rows = [
        row
        for row in rows
        if row.get("face_detected")
        and 20 <= row.get("brightness", 0) <= 245
        and row.get("sharpness_score", 0) >= 0.2
    ] or [
        row
        for row in rows
        if 20 <= row.get("brightness", 0) <= 245 and row.get("sharpness_score", 0) >= 0.2
    ] or rows

    fallback: list[dict] = []
    for row in _diverse_rows(usable_rows, limit=limit):
        start = max(0.0, float(row["timestamp"]) - 0.2)
        end = start + 1.4
        clip = _candidate_from_group(video, start, end, 1.4, [row])
        clip["highlight_score"] = round(max(4.2, row.get("highlight_score", 0)), 2)
        clip["recommended_usage"] = "fallback"
        clip["reason"] = "素材均衡兜底片段：该视频高分镜头较少，但仍会进入候选，避免只使用第一段素材"
        fallback.append(clip)
    return fallback


def _interleave_by_source(candidates: list[dict]) -> list[dict]:
    by_source: dict[str, list[dict]] = defaultdict(list)
    for candidate in sorted(candidates, key=lambda c: c["highlight_score"], reverse=True):
        by_source[candidate["source"]].append(candidate)

    ordered_sources = sorted(by_source)
    interleaved: list[dict] = []
    while any(by_source.values()):
        for source in ordered_sources:
            if by_source[source]:
                interleaved.append(by_source[source].pop(0))
    return interleaved


def _candidate_from_group(video: str, start: float, end: float, duration: float, group: list[dict]) -> dict:
    avg = lambda key: sum(float(r.get(key, 0)) for r in group) / len(group)
    score = avg("highlight_score")
    face_ratio = avg("face_ratio")
    crop_center = _avg_center(group)
    shot_size = _majority(group, "shot_size", "unknown")
    subject_position = _majority(group, "subject_position", "unknown")
    visual_tags = _merged_tags(group)
    usage = _recommended_usage(score, face_ratio, shot_size, visual_tags, group)
    return {
        "source": video,
        "start": round(start, 2),
        "end": round(end, 2),
        "duration": round(duration, 2),
        "highlight_score": round(score, 2),
        "face_ratio": round(face_ratio, 4),
        "crop_center": crop_center,
        "sharpness_score": round(avg("sharpness_score"), 2),
        "composition_score": round(avg("center_score"), 2),
        "atmosphere_score": round((avg("brightness_score") + avg("stability_score") + avg("stage_lighting_score")) / 3, 2),
        "shot_size": shot_size,
        "subject_position": subject_position,
        "motion_energy": _majority(group, "motion_energy", "unknown"),
        "stage_lighting_score": round(avg("stage_lighting_score"), 2),
        "visual_tags": visual_tags,
        "scene_role": _majority(group, "scene_role", "supporting"),
        "recommended_usage": usage,
        "reason": group[0].get("reason", "高光候选片段"),
    }


def _recommended_usage(score: float, face_ratio: float, shot_size: str, visual_tags: list[str], group: list[dict]) -> str:
    if score >= 8.2 and (face_ratio >= 0.12 or shot_size == "closeup"):
        return "opening"
    if "flash_or_white_frame" in visual_tags:
        return "transition"
    if "high_motion" in visual_tags or any(row.get("scene_role") == "beat_cut" for row in group):
        return "beat_cut"
    if shot_size in {"closeup", "medium_closeup"}:
        return "beauty_hold"
    return "supporting"


def _majority(group: list[dict], key: str, fallback: str) -> str:
    values = [str(row.get(key) or fallback) for row in group]
    return Counter(values).most_common(1)[0][0] if values else fallback


def _merged_tags(group: list[dict]) -> list[str]:
    tags: list[str] = []
    for row in group:
        for tag in row.get("visual_tags", []):
            if tag not in tags:
                tags.append(tag)
    return tags


def _avg_center(group: list[dict]) -> tuple[float, float] | None:
    centers = [row.get("face_center") for row in group if row.get("face_center")]
    if not centers:
        return None
    x = sum(float(center[0]) for center in centers) / len(centers)
    y = sum(float(center[1]) for center in centers) / len(centers)
    return (round(x, 4), round(y, 4))


def _diverse_rows(rows: list[dict], limit: int) -> list[dict]:
    rows_by_time = sorted(rows, key=lambda r: r.get("timestamp", 0))
    if len(rows_by_time) <= limit:
        return rows_by_time
    bucket_size = max(1, len(rows_by_time) // limit)
    selected = []
    for index in range(0, len(rows_by_time), bucket_size):
        bucket = rows_by_time[index : index + bucket_size]
        if not bucket:
            continue
        selected.append(max(bucket, key=lambda r: r.get("highlight_score", 0)))
        if len(selected) >= limit:
            break
    return selected
