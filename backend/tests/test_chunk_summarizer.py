# tests/test_chunk_summarizer.py
from unittest.mock import patch, MagicMock
from engine.nodes.chunk_summarizer import chunk_summarizer_node


def _mock_claude_response(content: str):
    mock = MagicMock()
    mock.content = content
    return mock


def test_summarizes_all_chunks():
    """모든 청크가 요약되는지 테스트"""
    state = {
        "chunks": ["청크1 내용", "청크2 내용"],
        "chunk_summaries": [],
        "ui_events": [],
        "progress": 0.2,
    }

    with patch("engine.nodes.chunk_summarizer._get_llm") as mock_get:
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = [
            _mock_claude_response("청크1 요약입니다"),
            _mock_claude_response("청크2 요약입니다"),
        ]
        mock_get.return_value = mock_llm
        result = chunk_summarizer_node(state)

    assert len(result["chunk_summaries"]) == 2
    assert result["chunk_summaries"][0] == "청크1 요약입니다"
    assert result["chunk_summaries"][1] == "청크2 요약입니다"


def test_empty_chunks():
    """빈 청크 리스트면 빈 결과"""
    state = {
        "chunks": [],
        "chunk_summaries": [],
        "ui_events": [],
        "progress": 0.2,
    }
    result = chunk_summarizer_node(state)
    assert result["chunk_summaries"] == []


def test_emits_progress_events():
    """청크 처리마다 progress 이벤트가 발행되는지 테스트"""
    state = {
        "chunks": ["청크1", "청크2", "청크3"],
        "chunk_summaries": [],
        "ui_events": [],
        "progress": 0.2,
    }

    with patch("engine.nodes.chunk_summarizer._get_llm") as mock_get:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _mock_claude_response("요약")
        mock_get.return_value = mock_llm
        result = chunk_summarizer_node(state)

    chunk_summary_events = [
        e for e in result["ui_events"] if e["action"] == "chunk_summary"
    ]
    assert len(chunk_summary_events) == 3
