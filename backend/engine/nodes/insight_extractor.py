# engine/nodes/insight_extractor.py
import json
import os
from difflib import SequenceMatcher
from typing import Dict
from openai import OpenAI
from engine.state import WebinarState, UIAction


def _get_client():
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))


def _is_similar(a: str, b: str, threshold: float = 0.5) -> bool:
    """Check if two strings are similar above threshold."""
    return SequenceMatcher(None, a, b).ratio() > threshold


SUMMARY_PROMPT = """발표 내용에서 **새로운 구체적 사실**만 1문장으로 추출하세요.

## 핵심 규칙
1. 기존 요약에 이미 있는 내용은 절대 반복하지 마세요
2. "~에 대해 논의/발표/이야기했다" 같은 메타 서술 금지
3. 구체적 사실·수치·결론이 없으면 반드시 빈 문자열 "" 반환
4. 기존 요약과 비슷한 내용이면 빈 문자열 "" 반환

## 기존 요약 (이 내용은 이미 기록됨 — 절대 반복 금지)
{existing_summary}

## 새로운 발표 내용 (여기서만 새로운 사실 추출)
{recent_sentences}

## 응답 (JSON 형식): 새로운 사실 1문장만, 없으면 빈 문자열
{{"insight": ""}}"""


def insight_extractor(state: WebinarState) -> Dict:
    all_refined = state.get("refined_sentences", [])
    last_idx = state.get("last_summarized_idx", 0)
    existing = state.get("summary_points", [])

    # Only use sentences that haven't been summarized yet
    new_sentences = all_refined[last_idx:]
    if not new_sentences:
        return {"ui_events": []}

    response = _get_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": SUMMARY_PROMPT.format(
                existing_summary="\n".join(f"- {s}" for s in existing) if existing else "(아직 없음)",
                recent_sentences="\n".join(f"{i+1}. {s}" for i, s in enumerate(new_sentences)),
            ),
        }],
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content)
    insight = result.get("insight", "").strip()

    # Always advance the index so we don't re-process these sentences
    updated_idx = len(all_refined)

    # Skip empty insights
    if not insight or len(insight) < 10:
        return {"last_summarized_idx": updated_idx, "ui_events": []}

    # Skip generic/meta descriptions
    skip_phrases = [
        "통찰을 제공", "발표했습니다", "논의했습니다", "다루었습니다",
        "다룰 예정", "이야기할 예정", "말씀드리", "집중하겠",
        "살펴보겠", "설명하겠", "소개하겠", "대해 이야기",
        "에 대해 다룰", "예정이다", "할 것이다", "에 대해 설명",
        "내용을 다루", "주제를 다루",
    ]
    if any(p in insight for p in skip_phrases):
        return {"last_summarized_idx": updated_idx, "ui_events": []}

    # Similarity-based deduplication
    for ex in existing:
        if _is_similar(insight, ex):
            return {"last_summarized_idx": updated_idx, "ui_events": []}

    return {
        "summary_points": [*existing, insight],
        "last_summarized_idx": updated_idx,
        "ui_events": [{
            "action": UIAction.UPDATE_SUMMARY,
            "data": {"point": insight, "index": len(existing)},
        }],
    }
