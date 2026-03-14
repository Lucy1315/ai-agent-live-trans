# engine/nodes/insight_generator.py
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


INSIGHT_PROMPT = """아래는 YouTube 영상의 통합 요약입니다.

{final_summary}

이 내용을 바탕으로 다음 세 가지를 마크다운 형식으로 작성해주세요:

## 핵심 시사점
- 이 영상에서 가장 중요한 포인트 3~5가지

## 향후 전망 및 트렌드
- 이 내용이 시사하는 미래 방향성과 트렌드

## 액션 아이템
- 시청자가 이 내용을 바탕으로 실행할 수 있는 구체적 행동 제안"""


def insight_generator_node(state: Dict) -> Dict:
    """LangGraph 노드: 통합 요약 기반 인사이트 생성"""
    final_summary = state.get("final_summary", "")

    if not final_summary:
        return {"insights": "", "ui_events": [], "progress": 1.0}

    prompt = INSIGHT_PROMPT.format(final_summary=final_summary)
    response = _get_llm().invoke(prompt)
    insights = response.content.strip() if hasattr(response, "content") else str(response)

    logger.info("Generated insights")

    return {
        "insights": insights,
        "progress": 1.0,
        "ui_events": [
            {"action": "insights", "data": {"insights": insights}},
            {"action": "progress", "data": {"phase": "complete", "progress": 1.0}},
            {"action": "complete", "data": {}},
        ],
    }
