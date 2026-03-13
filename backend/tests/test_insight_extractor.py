# tests/test_insight_extractor.py
import json
from unittest.mock import patch, MagicMock
from engine.nodes.insight_extractor import insight_extractor
from engine.state import UIAction


def test_insight_extractor_adds_summary():
    state = {
        "refined_sentences": ["문장1", "문장2", "문장3", "문장4", "문장5"],
        "summary_points": [],
        "ui_events": [],
    }

    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = json.dumps({
        "insight": "발표자가 핵심 개념을 소개했습니다."
    })

    with patch("engine.nodes.insight_extractor._client") as mock_client:
        mock_client.chat.completions.create.return_value = mock_resp
        result = insight_extractor(state)

    assert len(result["summary_points"]) == 1
    assert result["summary_points"][0] == "발표자가 핵심 개념을 소개했습니다."
    assert result["ui_events"][0]["action"] == UIAction.UPDATE_SUMMARY
