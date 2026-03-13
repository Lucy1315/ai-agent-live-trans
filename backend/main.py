# main.py
import asyncio
import json
import logging
import time
import os
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from engine.graph import build_graph
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

graph = build_graph()

CHUNK_INTERVAL = 2.0


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
            "ui_events": [],
        }

        try:
            from faster_whisper import WhisperModel
            import numpy as np
            model_name = os.getenv("WHISPER_MODEL", "base")
            whisper = WhisperModel(model_name, device="cpu", compute_type="int8")

            async for audio_chunk in source.stream_chunks(url):
                if not _active_sessions.get(session_id):
                    break

                start_time = time.monotonic()

                audio_np = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) / 32768.0
                segments, info = whisper.transcribe(audio_np, language="en")
                segments_list = list(segments)

                text = " ".join(
                    s.text for s in segments_list
                    if s.avg_logprob > -1.0
                ).strip()

                elapsed = time.monotonic() - start_time
                if elapsed > CHUNK_INTERVAL:
                    logger.warning(f"STT took {elapsed:.1f}s > {CHUNK_INTERVAL}s, dropping chunk")
                    continue

                if not text:
                    continue

                chunk_id += 1
                state["current_chunk_text"] = text
                state["audio_chunk"] = audio_chunk
                state["chunk_id"] = chunk_id
                state["ui_events"] = []

                result = await asyncio.to_thread(graph.invoke, state)

                for key in ["sentence_buffer", "is_sentence_end", "full_transcript",
                            "refined_sentences", "glossary_dict", "summary_points",
                            "new_terms_found"]:
                    if key in result:
                        state[key] = result[key]

                for event in result.get("ui_events", []):
                    action = event["action"]
                    # UIAction inherits from str but str() gives "UIAction.NAME",
                    # so use .value to get the raw string like "fast_subtitle"
                    if hasattr(action, "value"):
                        action = action.value
                    yield {
                        "event": action,
                        "data": json.dumps(event["data"], ensure_ascii=False),
                    }

        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield {
                "event": "error",
                "data": json.dumps({"message": str(e)}),
            }
        finally:
            _active_sessions.pop(session_id, None)
            await source.close()
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
