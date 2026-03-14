# tests/test_final_summarizer.py
from unittest.mock import patch, MagicMock
from engine.nodes.final_summarizer import final_summarizer_node


def _mock_response(content):
    mock = MagicMock()
    mock.content = content
    return mock


def test_generates_final_summary():
    state = {
        "chunk_summaries": ["파트1 요약", "파트2 요약"],
        "final_summary": "",
        "ui_events": [],
        "progress": 0.7,
    }
    with patch("engine.nodes.final_summarizer._get_llm") as mock_get:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _mock_response("통합 요약 결과")
        mock_get.return_value = mock_llm
        result = final_summarizer_node(state)

    assert result["final_summary"] == "통합 요약 결과"
    assert any(e["action"] == "final_summary" for e in result["ui_events"])


def test_empty_summaries():
    state = {
        "chunk_summaries": [],
        "final_summary": "",
        "ui_events": [],
        "progress": 0.7,
    }
    result = final_summarizer_node(state)
    assert result["final_summary"] == ""
