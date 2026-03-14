# main.py
import asyncio
import json
import logging
import os
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from engine.graph import build_graph
from engine.state import SubtitleAnalysisState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Live-Trans API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_active_sessions: dict[str, bool] = {}
_session_states: dict[str, dict] = {}
_summarize_now_flags: dict[str, bool] = {}

graph = build_graph()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/stream")
async def stream(url: str = Query(..., description="YouTube URL")):
    session_id = url

    async def event_generator():
        _active_sessions[session_id] = True

        state: SubtitleAnalysisState = {
            "url": url,
            "is_live": False,
            "raw_subtitles": [],
            "chunks": [],
            "chunk_summaries": [],
            "final_summary": "",
            "insights": "",
            "progress": 0.0,
            "ui_events": [],
        }
        _session_states[session_id] = state

        try:
            # 전체 파이프라인 실행 (blocking → thread)
            result = await asyncio.to_thread(graph.invoke, state)

            # state 업데이트
            for key in result:
                if key in state:
                    state[key] = result[key]

            # 누적된 UI 이벤트 전송
            for event in result.get("ui_events", []):
                action = event["action"]
                if hasattr(action, "value"):
                    action = action.value
                yield {
                    "event": action,
                    "data": json.dumps(event["data"], ensure_ascii=False),
                }

        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            yield {
                "event": "error",
                "data": json.dumps({"message": str(e)}),
            }
        finally:
            _active_sessions.pop(session_id, None)
            # 세션 저장
            try:
                out_dir = Path("exports")
                out_dir.mkdir(exist_ok=True)
                out_path = out_dir / f"session-{int(time.time())}.json"
                out_path.write_text(
                    json.dumps(
                        {
                            "url": url,
                            "subtitles": state.get("raw_subtitles", []),
                            "chunk_summaries": state.get("chunk_summaries", []),
                            "final_summary": state.get("final_summary", ""),
                            "insights": state.get("insights", ""),
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                )
                logger.info(f"Session exported to {out_path}")
            except Exception as export_err:
                logger.error(f"Failed to export: {export_err}")

    return EventSourceResponse(event_generator())


@app.post("/api/summarize-now")
async def summarize_now(url: str = Query(...)):
    """라이브 스트리밍 수동 요약 트리거"""
    _summarize_now_flags[url] = True
    return {"status": "triggered"}


@app.post("/api/stop")
async def stop(url: str = Query(...)):
    _active_sessions[url] = False
    return {"status": "stopped"}


@app.get("/api/export/markdown")
async def export_markdown(url: str = Query(...)):
    state = _session_states.get(url)
    if not state:
        return {"status": "error", "message": "No session found"}

    lines = [
        "# 영상 분석 노트",
        "",
        f"**URL:** {url}",
        f"**분석일:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
    ]

    final_summary = state.get("final_summary", "")
    if final_summary:
        lines.append("## 통합 요약")
        lines.append("")
        lines.append(final_summary)
        lines.append("")
        lines.append("---")
        lines.append("")

    insights = state.get("insights", "")
    if insights:
        lines.append(insights)
        lines.append("")
        lines.append("---")
        lines.append("")

    chunk_summaries = state.get("chunk_summaries", [])
    if chunk_summaries:
        lines.append("## 파트별 요약")
        lines.append("")
        for i, s in enumerate(chunk_summaries, 1):
            lines.append(f"### 파트 {i}")
            lines.append(s)
            lines.append("")

    return {"status": "ok", "markdown": "\n".join(lines)}
