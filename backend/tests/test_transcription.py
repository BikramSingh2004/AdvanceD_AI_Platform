"""Tests for transcription service."""

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestTranscription:
    """Test transcription functions."""

    def test_format_timestamp_seconds(self):
        """Test timestamp formatting for seconds."""
        from app.services.transcription import format_timestamp

        assert format_timestamp(0) == "00:00"
        assert format_timestamp(30) == "00:30"
        assert format_timestamp(90) == "01:30"

    def test_format_timestamp_minutes(self):
        """Test timestamp formatting for minutes."""
        from app.services.transcription import format_timestamp

        assert format_timestamp(60) == "01:00"
        assert format_timestamp(125) == "02:05"
        assert format_timestamp(599) == "09:59"

    def test_format_timestamp_hours(self):
        """Test timestamp formatting for hours."""
        from app.services.transcription import format_timestamp

        assert format_timestamp(3600) == "01:00:00"
        assert format_timestamp(3661) == "01:01:01"
        assert format_timestamp(7325) == "02:02:05"

    def test_find_timestamp_for_text(self):
        """Test finding timestamps for text."""
        from app.models import TimestampSegment
        from app.services.transcription import find_timestamp_for_text

        timestamps = [
            TimestampSegment(start=0.0, end=5.0, text="Hello world"),
            TimestampSegment(start=5.0, end=10.0, text="This is a test"),
            TimestampSegment(start=10.0, end=15.0, text="Hello again"),
        ]

        matches = find_timestamp_for_text(timestamps, "hello")

        assert len(matches) == 2
        assert matches[0]["start"] == 0.0
        assert matches[1]["start"] == 10.0

    def test_find_timestamp_for_text_no_match(self):
        """Test finding timestamps with no matches."""
        from app.models import TimestampSegment
        from app.services.transcription import find_timestamp_for_text

        timestamps = [
            TimestampSegment(start=0.0, end=5.0, text="Hello world"),
        ]

        matches = find_timestamp_for_text(timestamps, "goodbye")

        assert len(matches) == 0

    @pytest.mark.asyncio
    async def test_get_transcript_at_timestamp(self):
        """Test getting transcript at timestamp."""
        from app.models import TimestampSegment
        from app.services.transcription import get_transcript_at_timestamp

        timestamps = [
            TimestampSegment(start=0.0, end=5.0, text="Hello"),
            TimestampSegment(start=5.0, end=10.0, text="World"),
            TimestampSegment(start=10.0, end=15.0, text="Test"),
        ]

        result = await get_transcript_at_timestamp(timestamps, 7.5, context_seconds=5.0)

        assert "World" in result

    @pytest.mark.asyncio
    async def test_transcribe_media_mock(self, mock_whisper):
        """Test media transcription with mocked Whisper."""
        from app.services.transcription import transcribe_media

        with patch("app.services.transcription._transcribe_sync") as mock_sync:
            mock_sync.return_value = {
                "text": "Transcribed text",
                "timestamps": [],
                "language": "en",
            }

            result = await transcribe_media("test.mp3")

            assert result["text"] == "Transcribed text"
            assert result["language"] == "en"

    def test_transcribe_sync_audio(self, mock_whisper):
        """Test synchronous audio transcription."""
        from app.services.transcription import _transcribe_sync

        with patch("os.path.splitext", return_value=("test", ".mp3")):
            result = _transcribe_sync("test.mp3")

            assert "text" in result
            assert "timestamps" in result
            assert len(result["timestamps"]) == 2

    def test_transcribe_sync_video_extraction(self, mock_whisper):
        """Test video audio extraction."""
        from app.services.transcription import _transcribe_sync

        with patch("os.path.splitext", return_value=("test", ".mp4")):
            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                mock_temp.return_value.__enter__ = MagicMock(
                    return_value=MagicMock(name="temp.wav")
                )
                mock_temp.return_value.__exit__ = MagicMock(return_value=False)
                mock_temp.return_value.name = "temp.wav"
                mock_temp.return_value.close = MagicMock()

                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=0)

                    with patch("os.path.exists", return_value=True):
                        with patch("os.unlink"):
                            result = _transcribe_sync("test.mp4")

                            assert "text" in result
