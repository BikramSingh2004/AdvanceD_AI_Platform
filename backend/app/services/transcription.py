"""Audio/Video transcription service using OpenAI Whisper."""

import asyncio
import os
import subprocess
import tempfile
from typing import Any, Dict, List

from app.config import get_settings
from app.models import TimestampSegment

settings = get_settings()

# Global model cache
_whisper_model = None


def get_whisper_model():
    """Get or load Whisper model."""
    global _whisper_model
    if _whisper_model is None:
        import whisper

        _whisper_model = whisper.load_model(settings.whisper_model)
    return _whisper_model


async def transcribe_media(file_path: str) -> Dict[str, Any]:
    """
    Transcribe audio or video file using Whisper.

    Args:
        file_path: Path to the media file

    Returns:
        Dictionary with text and timestamps
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _transcribe_sync, file_path)


def _transcribe_sync(file_path: str) -> Dict[str, Any]:
    """Synchronous transcription."""
    # Check if it's a video file - extract audio first
    video_extensions = [".mp4", ".webm", ".mkv", ".avi", ".mov"]
    ext = os.path.splitext(file_path)[1].lower()

    audio_path = file_path
    temp_audio = None

    if ext in video_extensions:
        # Extract audio from video using ffmpeg
        temp_audio = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_audio.close()
        audio_path = temp_audio.name

        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-i",
                    file_path,
                    "-vn",  # No video
                    "-acodec",
                    "pcm_s16le",  # WAV format
                    "-ar",
                    "16000",  # 16kHz sample rate (Whisper preferred)
                    "-ac",
                    "1",  # Mono
                    "-y",  # Overwrite
                    audio_path,
                ],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            if temp_audio:
                os.unlink(audio_path)
            raise RuntimeError(f"Failed to extract audio: {e.stderr.decode()}")
        except FileNotFoundError:
            if temp_audio:
                os.unlink(audio_path)
            raise RuntimeError("ffmpeg not found. Please install ffmpeg.")

    try:
        # Load model and transcribe
        model = get_whisper_model()

        # Transcribe with word-level timestamps
        result = model.transcribe(
            audio_path,
            word_timestamps=True,
            verbose=False,
        )

        # Extract segments with timestamps
        timestamps = []
        for segment in result.get("segments", []):
            timestamps.append(
                TimestampSegment(
                    start=segment["start"],
                    end=segment["end"],
                    text=segment["text"].strip(),
                )
            )

        return {
            "text": result["text"],
            "timestamps": timestamps,
            "language": result.get("language", "en"),
        }

    finally:
        # Clean up temp audio file
        if temp_audio and os.path.exists(audio_path):
            os.unlink(audio_path)


async def get_transcript_at_timestamp(
    timestamps: List[TimestampSegment],
    time_seconds: float,
    context_seconds: float = 10.0,
) -> str:
    """
    Get transcript text around a specific timestamp.

    Args:
        timestamps: List of timestamp segments
        time_seconds: Target time in seconds
        context_seconds: Seconds of context before and after

    Returns:
        Transcript text around the timestamp
    """
    start_time = max(0, time_seconds - context_seconds)
    end_time = time_seconds + context_seconds

    relevant_segments = [
        ts for ts in timestamps if ts.start >= start_time and ts.end <= end_time
    ]

    return " ".join([ts.text for ts in relevant_segments])


def format_timestamp(seconds: float) -> str:
    """
    Format seconds as HH:MM:SS or MM:SS.

    Args:
        seconds: Time in seconds

    Returns:
        Formatted timestamp string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def find_timestamp_for_text(
    timestamps: List[TimestampSegment],
    search_text: str,
) -> List[Dict[str, Any]]:
    """
    Find timestamps where specific text appears.

    Args:
        timestamps: List of timestamp segments
        search_text: Text to search for

    Returns:
        List of matching timestamps with formatted time
    """
    search_lower = search_text.lower()
    matches = []

    for ts in timestamps:
        if search_lower in ts.text.lower():
            matches.append(
                {
                    "start": ts.start,
                    "end": ts.end,
                    "text": ts.text,
                    "formatted_start": format_timestamp(ts.start),
                    "formatted_end": format_timestamp(ts.end),
                }
            )

    return matches
