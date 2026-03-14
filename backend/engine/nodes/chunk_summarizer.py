# engine/nodes/chunk_summarizer.py
import os
import logging
from typing import Dict

logger = logging.getLogger(__name__)

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        from langchain_anthropic import ChatAnthropic
        _llm = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            max_tokens=2048,
        )
    return _llm


CHUNK_SUMMARY_PROMPT = """아래는 YouTube 영상의 한국어 자막 일부입니다.

이 내용의 핵심을 맥락에 맞게 요약해주세요.
- 주요 논점과 핵심 내용을 빠짐없이 포함
- 전문 용어가 있으면 그대로 유지
- 간결하되 중요한 세부사항은 보존

---
{chunk}
---

요약:"""


def chunk_summarizer_node(state: Dict) -> Dict:
    """LangGraph 노드: 각 청크를 Claude로 요약"""
    chunks = state.get("chunks", [])

    if not chunks:
        return {"chunk_summaries": [], "ui_events": [], "progress": 0.5}

    summaries = []
    ui_events = []

    for i, chunk in enumerate(chunks):
        prompt = CHUNK_SUMMARY_PROMPT.format(chunk=chunk)
        response = _get_llm().invoke(prompt)
        summary = response.content.strip() if hasattr(response, "content") else str(response)
        summaries.append(summary)

        progress = 0.2 + (0.5 * (i + 1) / len(chunks))
        ui_events.append({
            "action": "chunk_summary",
            "data": {"index": i, "summary": summary},
        })
        ui_events.append({
            "action": "progress",
            "data": {
                "phase": "summarizing",
                "progress": round(progress, 2),
                "chunk_index": i,
                "total_chunks": len(chunks),
            },
        })

        logger.info(f"Summarized chunk {i + 1}/{len(chunks)}")

    return {
        "chunk_summaries": summaries,
        "progress": 0.7,
        "ui_events": ui_events,
    }
