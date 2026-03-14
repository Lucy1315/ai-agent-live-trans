# engine/nodes/fast_translator.py
import os
from typing import Dict
from engine.state import WebinarState, UIAction


def _get_client():
    from openai import OpenAI
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))


SYSTEM_PROMPT = """당신은 실시간 동시통역사입니다. 영어 발표/웨비나 내용을 한국어로 통역합니다.

## 규칙
1. 자연스럽고 매끄러운 한국어로 번역하세요
2. 기술 용어는 원어를 병기하세요 (예: "약물 개발(Drug Development)")
3. 문장이 불완전해도 자연스럽게 의미를 전달하세요
4. 번역문만 출력하세요 (설명, 주석 없이)
5. 이전 맥락과 일관된 용어와 어투를 유지하세요"""


def fast_translator(state: WebinarState) -> Dict:
    # Use the fullest available text for better context:
    # 1. Completed sentence (from full_transcript) when sentence boundary detected
    # 2. Accumulated buffer (ongoing sentence) for partial translations
    # 3. Fall back to current chunk text
    transcript = state.get("full_transcript", [])
    buffer = state.get("sentence_buffer", "")

    if state.get("is_sentence_end") and transcript:
        text = transcript[-1]
    elif buffer.strip():
        text = buffer
    else:
        text = state.get("current_chunk_text", "")

    if not text.strip():
        return {"fast_translation": "", "ui_events": []}

    chunk_id = state.get("chunk_id", 0)
    glossary = state.get("glossary_dict", {})
    prev_translations = state.get("refined_sentences", [])[-3:]

    # Build context-aware prompt
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Add previous translations as conversation context
    if prev_translations or glossary:
        context_parts = []
        if prev_translations:
            context_parts.append("이전 번역:\n" + "\n".join(f"- {t}" for t in prev_translations))
        if glossary:
            terms = ", ".join(f"{k}({v})" for k, v in list(glossary.items())[-10:])
            context_parts.append(f"용어집: {terms}")
        messages.append({"role": "system", "content": "\n\n".join(context_parts)})

    messages.append({"role": "user", "content": text})

    client = _get_client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=500,
    )

    translation = response.choices[0].message.content.strip()

    return {
        "fast_translation": translation,
        "ui_events": [{
            "action": UIAction.UPDATE_FAST_SUBTITLE,
            "data": {"text": translation, "chunk_id": chunk_id},
        }],
    }
