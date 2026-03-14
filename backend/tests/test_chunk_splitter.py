# tests/test_chunk_splitter.py
from engine.nodes.chunk_splitter import chunk_splitter_node


def test_splits_by_time_window():
    """5분 단위로 청크가 분할되는지 테스트"""
    subtitles = [
        {"start": 0.0, "end": 10.0, "text": f"문장 {i}"}
        for i in range(60)
    ]
    for i, s in enumerate(subtitles):
        s["start"] = i * 10.0
        s["end"] = (i + 1) * 10.0

    state = {
        "raw_subtitles": subtitles,
        "chunks": [],
        "ui_events": [],
        "progress": 0.1,
    }
    result = chunk_splitter_node(state)
    assert len(result["chunks"]) == 2
    assert "문장 0" in result["chunks"][0]
    assert "문장 30" in result["chunks"][1]


def test_single_chunk_for_short_video():
    """5분 미만 영상은 1개 청크"""
    subtitles = [
        {"start": i * 5.0, "end": (i + 1) * 5.0, "text": f"짧은 문장 {i}"}
        for i in range(10)
    ]
    state = {
        "raw_subtitles": subtitles,
        "chunks": [],
        "ui_events": [],
        "progress": 0.1,
    }
    result = chunk_splitter_node(state)
    assert len(result["chunks"]) == 1


def test_empty_subtitles():
    """빈 자막이면 빈 청크"""
    state = {
        "raw_subtitles": [],
        "chunks": [],
        "ui_events": [],
        "progress": 0.1,
    }
    result = chunk_splitter_node(state)
    assert result["chunks"] == []
