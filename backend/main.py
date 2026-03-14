# main.py
import asyncio
import json
import logging
import time
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from engine.nodes.stt_node import stt_node
from engine.nodes.fast_translator import fast_translator
from engine.nodes.context_refiner import context_refiner
from engine.nodes.insight_extractor import insight_extractor
from engine.state import WebinarState
from sources.youtube import YouTubeSource

logger = logging.getLogger(__name__)

app = FastAPI(title="Live-Trans API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_active_sessions: dict[str, bool] = {}
_session_states: dict[str, dict] = {}

CHUNK_INTERVAL = 8.0


def _format_event(event: dict) -> dict:
    action = event["action"]
    if hasattr(action, "value"):
        action = action.value
    return {
        "event": action,
        "data": json.dumps(event["data"], ensure_ascii=False),
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/stream")
async def stream(url: str = Query(..., description="Audio source URL")):
    session_id = url

    async def event_generator():
        _active_sessions[session_id] = True
        source = YouTubeSource()
        chunk_id = 0

        state: WebinarState = {
            "audio_source_url": url,
            "audio_chunk": b"",
            "current_chunk_text": "",
            "is_sentence_end": False,
            "sentence_buffer": "",
            "chunk_id": 0,
            "fast_translation": "",
            "refined_translation": "",
            "refined_sentences": [],
            "new_terms_found": False,
            "full_transcript": [],
            "glossary_dict": {},
            "summary_points": [],
            "last_summarized_idx": 0,
            "ui_events": [],
        }
        _session_states[session_id] = state

        # Queue for background results (refined translation, glossary, insights)
        bg_queue: asyncio.Queue = asyncio.Queue()

        async def _run_background(state_snapshot: dict):
            """Run context_refiner + insight_extractor in background."""
            try:
                refiner_result = await asyncio.to_thread(context_refiner, state_snapshot)

                # Update shared state with refiner results
                for key in ["refined_sentences", "glossary_dict", "new_terms_found",
                            "refined_translation"]:
                    if key in refiner_result:
                        state[key] = refiner_result[key]

                for event in refiner_result.get("ui_events", []):
                    await bg_queue.put(_format_event(event))

                # Check if insight_extractor should run
                refined = state.get("refined_sentences", [])
                if len(refined) > 0 and len(refined) % 5 == 0:
                    insight_state = {**state}
                    insight_result = await asyncio.to_thread(insight_extractor, insight_state)

                    for key in ["summary_points", "last_summarized_idx"]:
                        if key in insight_result:
                            state[key] = insight_result[key]

                    for event in insight_result.get("ui_events", []):
                        await bg_queue.put(_format_event(event))

            except Exception as e:
                logger.error(f"Background processing error: {e}")

        try:
            from faster_whisper import WhisperModel
            import numpy as np
            model_name = os.getenv("WHISPER_MODEL", "base")
            whisper = WhisperModel(model_name, device="cpu", compute_type="int8")

            step_duration = source.chunk_duration - source.overlap  # 5 - 1 = 4s
            stream_start = None  # set on first chunk

            async for audio_chunk in source.stream_chunks(url):
                if not _active_sessions.get(session_id):
                    break

                # --- Drain background results first ---
                while not bg_queue.empty():
                    yield bg_queue.get_nowait()

                # --- Real-time throttle ---
                now = time.monotonic()
                if stream_start is None:
                    stream_start = now
                else:
                    target_time = stream_start + (chunk_id * step_duration)
                    wait = target_time - now
                    if wait > 0:
                        await asyncio.sleep(wait)

                def _transcribe(chunk):
                    audio_np = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
                    segs, _ = whisper.transcribe(audio_np, language="en")
                    return " ".join(
                        s.text for s in segs if s.avg_logprob > -1.0
                    ).strip()

                text = await asyncio.to_thread(_transcribe, audio_chunk)

                if not text:
                    chunk_id += 1
                    continue

                chunk_id += 1
                state["current_chunk_text"] = text
                state["audio_chunk"] = audio_chunk
                state["chunk_id"] = chunk_id

                # --- STT node (sentence boundary detection) ---
                stt_result = stt_node(state)
                for key in ["sentence_buffer", "is_sentence_end", "full_transcript",
                            "current_chunk_text"]:
                    if key in stt_result:
                        state[key] = stt_result[key]

                # --- Fast translation (always runs, yields immediately) ---
                fast_result = await asyncio.to_thread(fast_translator, state)
                state["fast_translation"] = fast_result.get("fast_translation", "")

                for event in fast_result.get("ui_events", []):
                    yield _format_event(event)

                # --- Background: context_refiner + insight_extractor ---
                if state.get("is_sentence_end"):
                    state_snapshot = {**state}
                    asyncio.create_task(_run_background(state_snapshot))

        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield {
                "event": "error",
                "data": json.dumps({"message": str(e)}),
            }
        finally:
            _active_sessions.pop(session_id, None)
            await source.close()

            # Drain any remaining background results
            while not bg_queue.empty():
                yield bg_queue.get_nowait()

            try:
                export = {
                    "transcript": state.get("full_transcript", []),
                    "glossary": state.get("glossary_dict", {}),
                    "summary": state.get("summary_points", []),
                }
                out_dir = Path("exports")
                out_dir.mkdir(exist_ok=True)
                out_path = out_dir / f"session-{int(time.time())}.json"
                out_path.write_text(json.dumps(export, ensure_ascii=False, indent=2))
                logger.info(f"Session exported to {out_path}")
            except Exception as export_err:
                logger.error(f"Failed to export session: {export_err}")

    return EventSourceResponse(event_generator())


@app.post("/api/stop")
async def stop(url: str = Query(...)):
    _active_sessions[url] = False
    return {"status": "stopped"}


@app.post("/api/final-summary")
async def final_summary(url: str = Query(...)):
    """세션의 요약 포인트들을 기반으로 최종 인사이트 요약 생성"""
    state = _session_states.get(url)
    if not state:
        return {"status": "error", "message": "세션을 찾을 수 없습니다"}

    summary_points = state.get("summary_points", [])
    glossary = state.get("glossary_dict", {})

    if not summary_points:
        return {"status": "ok", "final_summary": "", "insights": ""}

    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

    prompt = f"""다음은 실시간 웨비나/영상의 핵심 요약 포인트들입니다.

## 요약 포인트
{chr(10).join(f'{i+1}. {p}' for i, p in enumerate(summary_points))}

## 용어집
{json.dumps(glossary, ensure_ascii=False) if glossary else '(없음)'}

위 내용을 바탕으로 다음을 JSON 형식으로 작성해주세요:

1. "final_summary": 전체 내용의 통합 요약 (핵심 흐름과 맥락을 반영, 3~5문장)
2. "key_insights": 핵심 시사점 3~5가지 (리스트)
3. "trends": 향후 전망 및 트렌드 2~3가지 (리스트)
4. "action_items": 시청자가 실행할 수 있는 구체적 행동 제안 2~3가지 (리스트)"""

    response = await asyncio.to_thread(
        client.chat.completions.create,
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content)
    return {"status": "ok", **result}


@app.get("/api/export/markdown")
async def export_markdown(url: str = Query(...)):
    """세션 데이터를 마크다운으로 내보내기"""
    state = _session_states.get(url)
    if not state:
        return {"status": "error", "message": "세션을 찾을 수 없습니다"}

    summary_points = state.get("summary_points", [])
    glossary = state.get("glossary_dict", {})

    lines = [
        "# 영상 분석 노트",
        "",
        f"**분석일:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
    ]

    if summary_points:
        lines.append("## 핵심 요약")
        lines.append("")
        for i, point in enumerate(summary_points, 1):
            lines.append(f"{i}. {point}")
        lines.append("")
        lines.append("---")
        lines.append("")

    if glossary:
        lines.append("## 용어집")
        lines.append("")
        lines.append("| 용어 | 설명 |")
        lines.append("|------|------|")
        for term, definition in glossary.items():
            lines.append(f"| {term} | {definition} |")
        lines.append("")

    return {"status": "ok", "markdown": "\n".join(lines)}
