"""
BUG-019: transcriptsToday field has wrong type (str instead of int).

Tests that the DashboardMetrics model uses Optional[int].
"""

import os
import sys
import typing

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestTranscriptsTodayType:
    """BUG-019: transcriptsToday must be Optional[int], not Optional[str]."""

    def test_transcripts_today_accepts_int(self):
        """transcriptsToday should accept integer values."""
        from models.analytics import DashboardMetrics

        metrics = DashboardMetrics(
            total_calls_24h=100,
            active_playlists=5,
            transcripts_today=42,
            avg_transcription_confidence=0.85,
            processing_queue_size=0,
            api_calls_today=200,
            recent_calls=[],
            top_talkgroups=[],
            transcriptsToday=42,
        )
        assert metrics.transcriptsToday == 42
        assert isinstance(metrics.transcriptsToday, int)

    def test_transcripts_today_not_str_type(self):
        """transcriptsToday field annotation must not be Optional[str]."""
        from models.analytics import DashboardMetrics

        hints = typing.get_type_hints(DashboardMetrics)
        field_type = hints.get("transcriptsToday")

        # Should be Optional[int] which is Union[int, None]
        typing.get_origin(field_type)
        args = typing.get_args(field_type)

        assert str not in args, \
            f"transcriptsToday should be Optional[int], not Optional[str]. Got: {field_type}"
        assert int in args, \
            f"transcriptsToday should include int. Got: {field_type}"
