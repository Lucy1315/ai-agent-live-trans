# tests/test_context_refiner.py
import json
from unittest.mock import patch, MagicMock
from engine.nodes.context_refiner import context_refiner
from engine.state import UIAction


def _mock_openai_response(translation: str, terms: list):
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = json.dumps({
        "translation": translation,
        "terms": terms,
    })
    return mock_resp


def test_refiner_returns_translation_and_terms():
    state = {
        "sentence_buffer": "Today we discuss transformer architecture.",
        "refined_sentences": ["이전 문장입니다."],
        "glossary_dict": {},
        "chunk_id": 5,
        "ui_events": [],
    }

    mock_resp = _mock_openai_response(
        "오늘 트랜스포머 아키텍처에 대해 논의합니다.",
        [{"term": "Transformer", "definition": "자기 주의 메커니즘 기반 딥러닝 모델"}]
    )

    with patch("engine.nodes.context_refiner._client") as mock_client:
        mock_client.chat.completions.create.return_value = mock_resp
        result = context_refiner(state)

    assert result["refined_translation"] == "오늘 트랜스포머 아키텍처에 대해 논의합니다."
    assert "Transformer" in result["glossary_dict"]
    assert result["new_terms_found"] is True
    assert len(result["refined_sentences"]) == 2


def test_refiner_skips_existing_terms():
    state = {
        "sentence_buffer": "Transformers are great.",
        "refined_sentences": [],
        "glossary_dict": {"Transformer": "이미 있는 정의"},
        "chunk_id": 1,
        "ui_events": [],
    }

    mock_resp = _mock_openai_response(
        "트랜스포머는 훌륭합니다.",
        [{"term": "Transformer", "definition": "자기 주의 메커니즘 기반 딥러닝 모델"}]
    )

    with patch("engine.nodes.context_refiner._client") as mock_client:
        mock_client.chat.completions.create.return_value = mock_resp
        result = context_refiner(state)

    assert result["new_terms_found"] is False
    assert result["glossary_dict"] == {"Transformer": "이미 있는 정의"}
