from pathlib import Path


def analyze_bgm(bgm_path: Path, target_duration: int = 30) -> dict:
    try:
        import librosa

        y, sr = librosa.load(str(bgm_path), sr=None, mono=True, duration=max(45, target_duration + 5))
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
        beat_times = [round(float(t), 3) for t in beats if 0 <= float(t) <= target_duration]
        if not beat_times:
            beat_times = [round(i * 0.5, 3) for i in range(1, target_duration * 2)]
        strong_beats = beat_times[::4] or beat_times[::2]
        tempo_value = float(tempo[0] if hasattr(tempo, "__len__") else tempo)
    except Exception:
        tempo_value = 120.0
        beat_times = [round(i * 0.5, 3) for i in range(1, target_duration * 2)]
        strong_beats = beat_times[::4]

    return {
        "tempo": round(tempo_value, 2),
        "beats": beat_times,
        "strong_beats": strong_beats,
        "target_duration": target_duration,
    }
