# engine/nodes/context_refiner.py
import json
import os
from typing import Dict
from openai import OpenAI
from engine.state import WebinarState, UIAction

def _get_client():
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

REFINER_PROMPT = """당신은 전문 동시통역사입니다. 웨비나/발표 영상의 영어 발화를 한국어로 고품질 번역하세요.

## 번역 규칙
1. 발표 맥락에 맞는 자연스럽고 격식 있는 한국어를 사용하세요
2. 기술 용어는 한국어 번역과 원어를 병기하세요 (예: "약물 개발(Drug Development)")
3. 이전 맥락의 용어와 어투를 일관되게 유지하세요
4. 발화자의 의도와 뉘앙스를 정확히 전달하세요
5. 새로운 **전문 기술 용어**만 추출하세요 (기존 용어집에 없는 것만)

## 용어 추출 기준 (엄격히 준수)
- 추출 대상: 해당 분야의 전문 학술/기술 용어만 (예: Biosimilar, mRNA, ADCC, Pharmacokinetics)
- 추출 제외: 일반 영어 단어 (podcast, CEO, webinar, introduction, company, university 등)
- 추출 제외: 고유명사, 인명, 회사명, 브랜드명, 지명
- 추출 제외: 널리 알려진 약어 (MBA, R&D, AI, IT 등)
- 해당 발화에 전문 용어가 없으면 terms를 빈 배열 []로 반환

## 이전 맥락 (최근 번역)
{context}

## 기존 용어집
{glossary}

## 번역할 영어 원문
{sentence}

## 응답 형식 (JSON)
{{"translation": "한국어 번역", "terms": [{{"term": "영어 전문용어", "definition": "한국어 설명 (1줄)"}}]}}"""


def context_refiner(state: WebinarState) -> Dict:
    # When is_sentence_end=True, stt_node clears sentence_buffer but appends
    # the completed sentence to full_transcript. Read from there.
    transcript = state.get("full_transcript", [])
    sentence = transcript[-1] if transcript else ""
    if not sentence.strip():
        return {"refined_translation": "", "ui_events": []}

    context = state.get("refined_sentences", [])[-5:]
    glossary = state.get("glossary_dict", {})
    chunk_id = state.get("chunk_id", 0)

    response = _get_client().chat.completions.create(
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
