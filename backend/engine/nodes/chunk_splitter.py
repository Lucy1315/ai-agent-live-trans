# engine/nodes/chunk_splitter.py
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

CHUNK_DURATION_SECONDS = 300  # 5분


def chunk_splitter_node(state: Dict) -> Dict:
    """LangGraph 노드: 자막을 5분 단위 청크로 분할"""
    subtitles = state.get("raw_subtitles", [])

    if not subtitles:
        return {"chunks": [], "progress": 0.2, "ui_events": []}

    chunks = []
    current_chunk_texts: List[str] = []
    chunk_start_time = subtitles[0]["start"]

    for sub in subtitles:
        if sub["start"] - chunk_start_time >= CHUNK_DURATION_SECONDS and current_chunk_texts:
            chunks.append("\n".join(current_chunk_texts))
            current_chunk_texts = []
            chunk_start_time = sub["start"]
        current_chunk_texts.append(sub["text"])

    # 마지막 청크
    if current_chunk_texts:
        chunks.append("\n".join(current_chunk_texts))

    logger.info(f"Split {len(subtitles)} subtitles into {len(chunks)} chunks")

    return {
        "chunks": chunks,
        "progress": 0.2,
        "ui_events": [
            {
                "action": "progress",
                "data": {
                    "phase": "summarizing",
                    "progress": 0.2,
                    "total_chunks": len(chunks),
                },
            }
        ],
    }
