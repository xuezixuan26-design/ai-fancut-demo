from pathlib import Path
import tempfile

from app.utils.ffmpeg_utils import run_ffmpeg


VIDEO_AUDIO_EXTS = {".mp4", ".mov", ".m4v"}


def analyze_bgm(bgm_path: Path, target_duration: int | None = None) -> dict:
    try:
        import librosa

        with _audio_source(bgm_path) as audio_path:
            y, sr = librosa.load(str(audio_path), sr=None, mono=True)
            detected_duration_sec = max(1.0, float(librosa.get_duration(y=y, sr=sr)))
            detected_duration = int(max(1, round(detected_duration_sec)))
            effective_duration = int(target_duration or detected_duration)
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
            beat_times = [round(float(t), 3) for t in beats if 0 <= float(t) <= effective_duration]
            if not beat_times:
                beat_times = [round(i * 0.5, 3) for i in range(1, effective_duration * 2)]
            strong_beats = beat_times[::4] or beat_times[::2]
            tempo_value = float(tempo[0] if hasattr(tempo, "__len__") else tempo)
    except Exception:
        effective_duration = int(target_duration or 30)
        detected_duration_sec = float(effective_duration)
        tempo_value = 120.0
        beat_times = [round(i * 0.5, 3) for i in range(1, effective_duration * 2)]
        strong_beats = beat_times[::4]

    return {
        "tempo": round(tempo_value, 2),
        "beats": beat_times,
        "strong_beats": strong_beats,
        "target_duration": effective_duration,
        "audio_duration_sec": round(float(target_duration or detected_duration_sec), 3),
    }


class _audio_source:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.temp_dir: tempfile.TemporaryDirectory | None = None
        self.audio_path = path

    def __enter__(self) -> Path:
        if self.path.suffix.lower() not in VIDEO_AUDIO_EXTS:
            return self.path
        self.temp_dir = tempfile.TemporaryDirectory()
        self.audio_path = Path(self.temp_dir.name) / "bgm_audio.wav"
        run_ffmpeg(["-i", str(self.path), "-vn", "-ac", "1", "-ar", "44100", str(self.audio_path)])
        return self.audio_path

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.temp_dir:
            self.temp_dir.cleanup()
