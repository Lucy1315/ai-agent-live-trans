# engine/nodes/fast_translator.py
from typing import Dict
from engine.state import WebinarState, UIAction

_initialized = False


def _ensure_model():
    global _initialized
    if _initialized:
        return
    import argostranslate.package
    argostranslate.package.update_package_index()
    available = argostranslate.package.get_available_packages()
    pkg = next((p for p in available
                if p.from_code == "en" and p.to_code == "ko"), None)
    if pkg:
        argostranslate.package.install_from_path(pkg.download())
    _initialized = True


def _translate(text: str) -> str:
    import argostranslate.translate
    _ensure_model()
    return argostranslate.translate.translate(text, "en", "ko")


def fast_translator(state: WebinarState) -> Dict:
    text = state.get("current_chunk_text", "")
    if not text.strip():
        return {"fast_translation": "", "ui_events": []}

    translation = _translate(text)
    chunk_id = state.get("chunk_id", 0)

    return {
        "fast_translation": translation,
        "ui_events": [{
            "action": UIAction.UPDATE_FAST_SUBTITLE,
            "data": {"text": translation, "chunk_id": chunk_id},
        }],
    }
