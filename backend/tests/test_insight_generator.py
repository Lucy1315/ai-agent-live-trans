# tests/test_insight_generator.py
from unittest.mock import patch, MagicMock
from engine.nodes.insight_generator import insight_generator_node


def _mock_response(content):
    mock = MagicMock()
    mock.content = content
    return mock


def test_generates_insights():
    state = {
        "final_summary": "AI 기술의 발전과 활용에 대한 요약",
        "insights": "",
        "ui_events": [],
        "progress": 0.85,
    }
    with patch("engine.nodes.insight_generator._get_llm") as mock_get:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _mock_response("## 핵심 시사점\n- 포인트1")
        mock_get.return_value = mock_llm
        result = insight_generator_node(state)

    assert "핵심 시사점" in result["insights"]
    assert result["progress"] == 1.0
    assert any(e["action"] == "insights" for e in result["ui_events"])
    assert any(e["action"] == "complete" for e in result["ui_events"])


def test_empty_summary():
    state = {
        "final_summary": "",
        "insights": "",
        "ui_events": [],
        "progress": 0.85,
    }
    result = insight_generator_node(state)
    assert result["insights"] == ""
