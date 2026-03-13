from engine.state import WebinarState, UIAction

def test_webinar_state_has_required_fields():
    state: WebinarState = {
        "audio_source_url": "https://youtube.com/watch?v=test",
        "audio_chunk": b"",
        "current_chunk_text": "",
        "is_sentence_end": False,
        "sentence_buffer": "",
        "chunk_id": 0,
        "fast_translation": "",
        "refined_translation": "",
        "refined_sentences": [],
        "new_terms_found": False,
        "full_transcript": [],
        "glossary_dict": {},
        "summary_points": [],
        "ui_events": [],
    }
    assert state["audio_source_url"] == "https://youtube.com/watch?v=test"
    assert state["chunk_id"] == 0

def test_ui_action_enum():
    assert UIAction.UPDATE_FAST_SUBTITLE == "fast_subtitle"
    assert UIAction.UPDATE_REFINED_SUBTITLE == "refined_subtitle"
    assert UIAction.UPDATE_GLOSSARY == "glossary"
    assert UIAction.UPDATE_SUMMARY == "summary"
