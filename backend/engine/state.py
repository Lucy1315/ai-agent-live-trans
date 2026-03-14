# engine/state.py
from typing import TypedDict, List, Dict
from enum import Enum


class UIAction(str, Enum):
    UPDATE_FAST_SUBTITLE = "fast_translation"
    UPDATE_REFINED_SUBTITLE = "refined_translation"
    UPDATE_GLOSSARY = "glossary"
    UPDATE_SUMMARY = "insights"


class WebinarState(TypedDict):
    # 입력
    audio_source_url: str
    audio_chunk: bytes

    # STT 출력
    current_chunk_text: str
    is_sentence_end: bool
    sentence_buffer: str
    chunk_id: int

    # Fast Track
    fast_translation: str

    # Slow Track
    refined_translation: str
    refined_sentences: List[str]
    new_terms_found: bool

    # 누적 데이터
    full_transcript: List[str]
    glossary_dict: Dict[str, str]
    summary_points: List[str]
    last_summarized_idx: int

    # UI 이벤트 큐
    ui_events: List[Dict]
