# engine/nodes/context_refiner.py
import json
import os
from typing import Dict
from openai import OpenAI
from engine.state import WebinarState, UIAction

_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

REFINER_PROMPT = """당신은 전문 통번역사입니다. 아래 영어 문장을 한국어로 번역하세요.

## 규칙
1. 기술 용어는 원어를 병기하세요 (예: "자연어 처리(NLP)")
2. 이전 맥락을 참고하여 일관된 용어를 사용하세요
3. 새로운 전문 용어가 있으면 추출하세요 (기존 용어집에 없는 것만)

## 이전 맥락 (최근 3문장)
{context}

## 기존 용어집
{glossary}

## 번역할 문장
{sentence}

## 응답 형식 (JSON)
{{"translation": "한국어 번역", "terms": [{{"term": "영어 용어", "definition": "한국어 설명 (1줄)"}}]}}"""


def context_refiner(state: WebinarState) -> Dict:
    sentence = state.get("sentence_buffer", "")
    if not sentence.strip():
        return {"refined_translation": "", "ui_events": []}

    context = state.get("refined_sentences", [])[-3:]
    glossary = state.get("glossary_dict", {})
    chunk_id = state.get("chunk_id", 0)

    response = _client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": REFINER_PROMPT.format(
                context="\n".join(context) if context else "(없음)",
                glossary=json.dumps(glossary, ensure_ascii=False) if glossary else "(없음)",
                sentence=sentence,
            ),
        }],
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content)
    translation = result.get("translation", "")
    raw_terms = result.get("terms", [])

    new_terms = {
        t["term"]: t["definition"]
        for t in raw_terms
        if t["term"] not in glossary
    }

    updated_glossary = {**glossary, **new_terms}
    updated_sentences = [*state.get("refined_sentences", []), translation]

    if len(updated_sentences) > 20:
        updated_sentences = updated_sentences[-20:]

    ui_events = [{
        "action": UIAction.UPDATE_REFINED_SUBTITLE,
        "data": {"text": translation, "chunk_id": chunk_id},
    }]

    if new_terms:
        ui_events.append({
            "action": UIAction.UPDATE_GLOSSARY,
            "data": new_terms,
        })

    return {
        "refined_translation": translation,
        "refined_sentences": updated_sentences,
        "new_terms_found": len(new_terms) > 0,
        "glossary_dict": updated_glossary,
        "ui_events": ui_events,
    }
