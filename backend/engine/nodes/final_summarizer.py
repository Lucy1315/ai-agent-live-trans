# engine/nodes/final_summarizer.py
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
            max_tokens=4096,
        )
    return _llm


FINAL_SUMMARY_PROMPT = """아래는 YouTube 영상의 각 파트별 요약입니다.

{chunk_summaries}

위 내용을 바탕으로 영상 전체의 통합 요약을 작성해주세요:
- 전체 흐름과 맥락을 반영한 구조화된 요약
- 주제별로 그루핑하여 정리
- 핵심 논점과 결론을 명확히
- 마크다운 형식으로 작성"""


def final_summarizer_node(state: Dict) -> Dict:
    """LangGraph 노드: 청크 요약들을 통합하여 최종 요약 생성"""
    chunk_summaries = state.get("chunk_summaries", [])

    if not chunk_summaries:
        return {"final_summary": "", "ui_events": [], "progress": 0.85}

    numbered = "\n\n".join(
        f"### 파트 {i + 1}\n{s}" for i, s in enumerate(chunk_summaries)
    )
    prompt = FINAL_SUMMARY_PROMPT.format(chunk_summaries=numbered)
    response = _get_llm().invoke(prompt)
    summary = response.content.strip() if hasattr(response, "content") else str(response)

    logger.info("Generated final summary")

    return {
        "final_summary": summary,
        "progress": 0.85,
        "ui_events": [
            {"action": "final_summary", "data": {"summary": summary}},
            {"action": "progress", "data": {"phase": "finalizing", "progress": 0.85}},
        ],
    }
