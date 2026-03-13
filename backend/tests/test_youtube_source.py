import pytest
from sources.base import AudioSource
from sources.youtube import YouTubeSource


def test_youtube_source_is_audio_source():
    source = YouTubeSource()
    assert isinstance(source, AudioSource)


def test_youtube_source_chunk_config():
    source = YouTubeSource(chunk_duration=2.0, overlap=0.5, sample_rate=16000)
    assert source.chunk_duration == 2.0
    assert source.overlap == 0.5
    assert source.sample_rate == 16000
