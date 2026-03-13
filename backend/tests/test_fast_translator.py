# tests/test_fast_translator.py
from unittest.mock import patch
from engine.nodes.fast_translator import fast_translator
from engine.state import UIAction


def test_fast_translator_returns_translation_and_event():
    state = {
        "current_chunk_text": "Hello world",
        "chunk_id": 1,
        "ui_events": [],
    }
    with patch("engine.nodes.fast_translator._translate", return_value="안녕 세계"):
        result = fast_translator(state)

    assert result["fast_translation"] == "안녕 세계"
    assert len(result["ui_events"]) == 1
    event = result["ui_events"][0]
    assert event["action"] == UIAction.UPDATE_FAST_SUBTITLE
    assert event["data"]["text"] == "안녕 세계"
    assert event["data"]["chunk_id"] == 1


def test_fast_translator_empty_text():
    state = {
        "current_chunk_text": "",
        "chunk_id": 2,
        "ui_events": [],
    }
    result = fast_translator(state)
    assert result["fast_translation"] == ""
    assert result["ui_events"] == []
