"""Local speech extraction runs in a separately time-bounded controller subprocess."""
import sys
import subprocess
import tempfile
import os


def main(path):
    with tempfile.NamedTemporaryFile(suffix=".wav") as audio:
        subprocess.run(["ffmpeg", "-protocol_whitelist", "file,pipe", "-v", "error", "-y", "-i", path,
                        "-vn", "-ac", "1", "-ar", "16000", audio.name], check=True, timeout=120)
        if os.environ.get('X_CURATOR_SPEECH_CONFIG'):
            from .speech_client import transcribe
            print(transcribe(audio.name, os.environ['X_CURATOR_SPEECH_CONFIG']))
            return
        from faster_whisper import WhisperModel
        model = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=2)
        segments, _ = model.transcribe(audio.name, beam_size=5, vad_filter=True)
        for segment in segments:
            print(f"[{segment.start:.1f}-{segment.end:.1f}] {segment.text.strip()}")


if __name__ == "__main__":
    main(sys.argv[1])
