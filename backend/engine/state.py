# engine/state.py
import operator
from typing import TypedDict, List, Dict, Annotated
from enum import Enum


class UIAction(str, Enum):
    SUBTITLES = "subtitles"
    PROGRESS = "progress"
    CHUNK_SUMMARY = "chunk_summary"
    FINAL_SUMMARY = "final_summary"
    INSIGHTS = "insights"
    ERROR = "error"
    COMPLETE = "complete"


class SubtitleAnalysisState(TypedDict):
    # Input
    url: str
    is_live: bool

    # Extracted subtitles
    raw_subtitles: Annotated[List[Dict], operator.add]  # [{start, end, text}]

    # Chunked data
    chunks: Annotated[List[str], operator.add]

    # Summaries
    chunk_summaries: Annotated[List[str], operator.add]
    final_summary: str
    insights: str

    # Progress & UI
    progress: float
    ui_events: Annotated[List[Dict], operator.add]  # 노드 간 누적
