from typing import TypedDict, List, Dict
from enum import Enum


class UIAction(str, Enum):
    UPDATE_FAST_SUBTITLE = "fast_subtitle"
    UPDATE_REFINED_SUBTITLE = "refined_subtitle"
    UPDATE_GLOSSARY = "glossary"
    UPDATE_SUMMARY = "summary"


class WebinarState(TypedDict):
    # Input
    audio_source_url: str
    audio_chunk: bytes

    # STT output
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

    # Accumulated data
    full_transcript: List[str]
    glossary_dict: Dict[str, str]
    summary_points: List[str]
    last_summarized_idx: int

    # UI event queue
    ui_events: List[Dict]
