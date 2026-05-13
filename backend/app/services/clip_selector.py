from collections import defaultdict


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
            avg = lambda key: sum(r[key] for r in group) / len(group)
            score = avg("highlight_score")
            usage = "opening" if score >= 8.2 and avg("face_ratio") >= 0.12 else "beat_cut"
            candidates.append(
                {
                    "source": video,
                    "start": round(start, 2),
                    "end": round(end, 2),
                    "duration": round(duration, 2),
                    "highlight_score": round(score, 2),
                    "face_ratio": round(avg("face_ratio"), 4),
                    "sharpness_score": round(avg("sharpness_score"), 2),
                    "composition_score": round(avg("center_score"), 2),
                    "atmosphere_score": round((avg("brightness_score") + avg("stability_score")) / 2, 2),
                    "recommended_usage": usage,
                    "reason": group[0].get("reason", "高光候选片段"),
                }
            )

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
            fallback.append(
                {
                    "source": video,
                    "start": round(start, 2),
                    "end": round(end, 2),
                    "duration": 1.4,
                    "highlight_score": round(max(4.8, row.get("highlight_score", 0)), 2),
                    "face_ratio": row.get("face_ratio", 0),
                    "sharpness_score": row.get("sharpness_score", 0),
                    "composition_score": row.get("center_score", 0),
                    "atmosphere_score": round((row.get("brightness_score", 0) + row.get("stability_score", 0)) / 2, 2),
                    "recommended_usage": "fallback",
                    "reason": "未检测到稳定人脸，使用清晰度和亮度较好的画面兜底测试",
                }
            )
    return sorted(fallback, key=lambda c: c["highlight_score"], reverse=True)
