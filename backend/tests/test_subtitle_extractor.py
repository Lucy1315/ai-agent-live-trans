# tests/test_subtitle_extractor.py
import pytest
from unittest.mock import patch, AsyncMock
from engine.nodes.subtitle_extractor import extract_subtitles_sync, subtitle_extractor_node


def test_parse_vtt_content():
    """VTT 자막 파싱이 올바르게 동작하는지 테스트"""
    from engine.nodes.subtitle_extractor import parse_vtt

    vtt_content = """WEBVTT

00:00:01.000 --> 00:00:04.000
안녕하세요 여러분

00:00:04.000 --> 00:00:08.000
오늘은 AI에 대해 이야기하겠습니다

00:00:08.000 --> 00:00:12.000
먼저 기본 개념부터 살펴보겠습니다
"""
    result = parse_vtt(vtt_content)
    assert len(result) == 3
    assert result[0]["text"] == "안녕하세요 여러분"
    assert result[0]["start"] == 1.0
    assert result[0]["end"] == 4.0
    assert result[1]["text"] == "오늘은 AI에 대해 이야기하겠습니다"


def test_parse_vtt_deduplicates():
    """중복 자막 라인 제거 테스트"""
    from engine.nodes.subtitle_extractor import parse_vtt

    vtt_content = """WEBVTT

00:00:01.000 --> 00:00:04.000
안녕하세요 여러분

00:00:02.000 --> 00:00:05.000
안녕하세요 여러분

00:00:04.000 --> 00:00:08.000
오늘은 AI에 대해 이야기하겠습니다
"""
    result = parse_vtt(vtt_content)
    assert len(result) == 2


def test_subtitle_extractor_node_sets_state():
    """노드가 state를 올바르게 업데이트하는지 테스트"""
    mock_subtitles = [
        {"start": 0.0, "end": 3.0, "text": "테스트 자막"},
    ]
    with patch(
        "engine.nodes.subtitle_extractor.extract_subtitles_sync",
        return_value=mock_subtitles,
    ):
        state = {
            "url": "https://youtube.com/watch?v=test123",
            "is_live": False,
            "raw_subtitles": [],
            "chunks": [],
            "chunk_summaries": [],
            "final_summary": "",
            "insights": "",
            "progress": 0.0,
            "ui_events": [],
        }
        result = subtitle_extractor_node(state)
        assert len(result["raw_subtitles"]) == 1
        assert result["raw_subtitles"][0]["text"] == "테스트 자막"
        assert result["progress"] == 0.1
