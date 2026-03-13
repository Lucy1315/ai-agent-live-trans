import pysbd
from difflib import SequenceMatcher
from typing import Dict
from engine.state import WebinarState

_segmenter = pysbd.Segmenter(language="en", clean=False)


def detect_sentence_end(text: str) -> bool:
    """Use pysbd to detect if text contains a complete sentence."""
    text = text.strip()
    if not text:
        return False
    sentences = _segmenter.segment(text)
    if len(sentences) > 1:
        return True
    # Single segment — check if it ends with sentence-ending punctuation
    # pysbd handles abbreviations like "e.g." correctly
    last = sentences[-1].strip()
    if last and last[-1] in ".?!":
        # Re-segment to confirm it's a real sentence end, not abbreviation
        test = _segmenter.segment(last)
        return len(test) == 1 and last[-1] in ".?!"
    return False


def deduplicate_overlap(prev_text: str, curr_text: str) -> str:
    """Remove overlapping prefix from curr_text that matches prev_text suffix."""
    prev_words = prev_text.split()
    curr_words = curr_text.split()

    if not prev_words or not curr_words:
        return curr_text

    max_overlap = min(len(prev_words), len(curr_words))
    best = 0

    for size in range(1, max_overlap + 1):
        if prev_words[-size:] == curr_words[:size]:
            best = size

    if best > 0:
        return " ".join(curr_words[best:])
    return curr_text


def stt_node(state: WebinarState) -> Dict:
    """LangGraph node: transcribe audio chunk and detect sentence boundaries."""
    chunk_text = state["current_chunk_text"]
    prev_buffer = state.get("sentence_buffer", "")

    # Deduplicate overlap with previous chunk
    if prev_buffer:
        chunk_text = deduplicate_overlap(prev_buffer, chunk_text)

    # Accumulate buffer
    new_buffer = f"{prev_buffer} {chunk_text}".strip() if prev_buffer else chunk_text
    is_end = detect_sentence_end(new_buffer)

    result = {
        "current_chunk_text": chunk_text,
        "sentence_buffer": new_buffer if not is_end else "",
        "is_sentence_end": is_end,
        "full_transcript": [*state.get("full_transcript", [])],
    }

    if is_end:
        result["full_transcript"].append(new_buffer)

    return result
