# engine/nodes/insight_extractor.py
import json
import os
from typing import Dict
from openai import OpenAI
from engine.state import WebinarState, UIAction

_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

SUMMARY_PROMPT = """다음은 웨비나 발표 내용의 번역본입니다.
핵심 포인트를 1~2문장으로 요약하세요.

## 기존 요약
{existing_summary}

## 최근 5문장
{recent_sentences}

## 응답 형식 (JSON)
{{"insight": "새로운 핵심 포인트 요약"}}"""


def insight_extractor(state: WebinarState) -> Dict:
    recent = state.get("refined_sentences", [])[-5:]
    existing = state.get("summary_points", [])

    response = _client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": SUMMARY_PROMPT.format(
                existing_summary="\n".join(existing) if existing else "(없음)",
                recent_sentences="\n".join(recent),
            ),
        }],
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content)
    insight = result.get("insight", "")

    return {
        "summary_points": [*existing, insight],
        "ui_events": [{
            "action": UIAction.UPDATE_SUMMARY,
            "data": {"point": insight, "index": len(existing)},
        }],
    }
