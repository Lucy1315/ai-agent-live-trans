# tests/test_state.py
from engine.state import SubtitleAnalysisState, UIAction


def test_subtitle_analysis_state_has_required_fields():
    state: SubtitleAnalysisState = {
        "url": "https://youtube.com/watch?v=test",
        "is_live": False,
        "raw_subtitles": [],
        "chunks": [],
        "chunk_summaries": [],
        "final_summary": "",
        "insights": "",
        "progress": 0.0,
        "ui_events": [],
    }
    assert state["url"] == "https://youtube.com/watch?v=test"
    assert state["is_live"] is False
    assert state["progress"] == 0.0


def test_ui_action_enum():
    assert UIAction.SUBTITLES == "subtitles"
    assert UIAction.PROGRESS == "progress"
    assert UIAction.CHUNK_SUMMARY == "chunk_summary"
    assert UIAction.FINAL_SUMMARY == "final_summary"
    assert UIAction.INSIGHTS == "insights"
    assert UIAction.ERROR == "error"
    assert UIAction.COMPLETE == "complete"
