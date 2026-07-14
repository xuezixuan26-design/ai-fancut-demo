from collections import Counter, defaultdict


def select_candidate_clips(frame_rows: list[dict], max_per_video: int = 16) -> list[dict]:
    by_video: dict[str, list[dict]] = defaultdict(list)
    for row in frame_rows:
        by_video[row["video"]].append(row)

    candidates: list[dict] = []
    for video, rows in by_video.items():
        rows = sorted(rows, key=lambda r: r["timestamp"])
        groups: list[list[dict]] = []
        current: list[dict] = []
        for row in rows:
            valid = (
                row["face_detected"]
                and row["highlight_score"] >= 5.6
                and 60 <= row["brightness"] <= 205
                and row["sharpness_score"] >= 3.0
            )
            if valid:
                current.append(row)
            elif current:
                groups.append(current)
                current = []
        if current:
            groups.append(current)

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

    selected: list[dict] = []
    for video in by_video:
        video_candidates = [c for c in candidates if c["source"] == video]
        selected.extend(sorted(video_candidates, key=lambda c: c["highlight_score"], reverse=True)[:max_per_video])
    selected = sorted(selected, key=lambda c: c["highlight_score"], reverse=True)
    if selected:
        return selected

    # Demo fallback: if face detection is too strict for the uploaded material,
    # still produce a few visually usable clips so the full render path can be tested.
    fallback: list[dict] = []
    for video, rows in by_video.items():
        usable_rows = [
            row
            for row in rows
            if 45 <= row.get("brightness", 0) <= 220 and row.get("sharpness_score", 0) >= 1.0
        ] or rows
        for row in sorted(usable_rows, key=lambda r: r.get("highlight_score", 0), reverse=True)[: min(4, max_per_video)]:
            start = max(0.0, float(row["timestamp"]) - 0.2)
            end = start + 1.4
            clip = _candidate_from_group(video, start, end, 1.4, [row])
            clip["highlight_score"] = round(max(4.8, row.get("highlight_score", 0)), 2)
            clip["recommended_usage"] = "fallback"
            clip["reason"] = "未检测到稳定人脸，使用清晰度和亮度较好的画面兜底测试"
            fallback.append(clip)
    return sorted(fallback, key=lambda c: c["highlight_score"], reverse=True)


def _candidate_from_group(video: str, start: float, end: float, duration: float, group: list[dict]) -> dict:
    avg = lambda key: sum(float(r.get(key, 0)) for r in group) / len(group)
    score = avg("highlight_score")
    face_ratio = avg("face_ratio")
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
