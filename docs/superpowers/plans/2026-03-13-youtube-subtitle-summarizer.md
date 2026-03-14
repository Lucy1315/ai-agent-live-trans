# YouTube 자막 기반 요약/인사이트 LangGraph 에이전트 구현 계획

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 기존 Audio→STT→GPT 번역 파이프라인을 YouTube 자막 추출 → Claude 기반 요약/인사이트 파이프라인으로 교체

**Architecture:** yt-dlp로 YouTube 한국어 자동번역 자막을 추출하고, LangGraph StateGraph로 청크 분할 → 청크별 요약 → 통합 요약 → 인사이트 생성을 순차 실행. FastAPI SSE로 진행상황 실시간 전송. State의 리스트 필드는 `Annotated[List, operator.add]` 리듀서를 사용하여 노드 간 누적.

**Phase 1 (이 계획):** 녹화 영상 일괄 처리 파이프라인
**Phase 2 (후속):** 라이브 스트리밍 폴링 모드 + 주기적 요약

**Tech Stack:** LangGraph, langchain-anthropic (Claude), yt-dlp, FastAPI, SSE, Next.js

**Spec:** `docs/superpowers/specs/2026-03-13-youtube-subtitle-summarizer-design.md`

---

## 파일 구조

### 백엔드 — 생성
| 파일 | 역할 |
|------|------|
| `backend/engine/nodes/subtitle_extractor.py` | yt-dlp로 YouTube 한국어 자막 추출 |
| `backend/engine/nodes/chunk_splitter.py` | 자막을 시간/분량 기준 청크 분할 |
| `backend/engine/nodes/chunk_summarizer.py` | Claude로 각 청크 요약 |
| `backend/engine/nodes/final_summarizer.py` | 청크 요약 통합 |
| `backend/engine/nodes/insight_generator.py` | 인사이트 생성 |
| `backend/tests/test_subtitle_extractor.py` | 자막 추출 테스트 |
| `backend/tests/test_chunk_splitter.py` | 청크 분할 테스트 |
| `backend/tests/test_chunk_summarizer.py` | 청크 요약 테스트 |
| `backend/tests/test_new_graph.py` | 새 그래프 라우팅 테스트 |
| `backend/tests/test_new_api.py` | 새 API 엔드포인트 테스트 |

### 백엔드 — 수정
| 파일 | 변경 |
|------|------|
| `backend/engine/state.py` | `SubtitleAnalysisState`로 교체 |
| `backend/engine/graph.py` | 새 파이프라인 그래프로 교체 |
| `backend/main.py` | API 엔드포인트 간소화 + summarize-now 추가 |
| `backend/requirements.txt` | langchain-anthropic 추가, 불필요 패키지 제거 |

### 프론트엔드 — 수정
| 파일 | 변경 |
|------|------|
| `frontend/hooks/useSSE.ts` | 새 SSE 이벤트 구조에 맞게 변경 |
| `frontend/app/page.tsx` | UI 간소화 (불필요 옵션 제거, 진행률/인사이트 추가) |
| `frontend/components/InsightPanel.tsx` | 요약+인사이트 분리 표시 |
| `frontend/components/ControlBar.tsx` | "지금 요약" 버튼 추가, glossary 제거 |
| `frontend/components/SubtitleDisplay.tsx` | 자막 목록 표시로 변경 |

### 삭제 대상
| 파일 | 이유 |
|------|------|
| `backend/engine/nodes/stt_node.py` | STT 불필요 |
| `backend/engine/nodes/translator.py` | 번역 불필요 |
| `backend/engine/nodes/summarizer.py` | 새 summarizer로 대체 |
| `backend/engine/nodes/fast_translator.py` | 불필요 |
| `backend/engine/nodes/context_refiner.py` | 불필요 |
| `backend/sources/base.py` | 오디오 소스 불필요 |
| `backend/sources/youtube.py` | 오디오 소스 불필요 |
| `frontend/components/GlossaryPanel.tsx` | 용어집 불필요 |

---

## Chunk 1: 백엔드 핵심 파이프라인

### Task 1: 의존성 업데이트 및 State 정의

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/engine/state.py`

- [ ] **Step 1: requirements.txt 업데이트**

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
sse-starlette==2.2.1
langgraph==0.2.60
langchain-anthropic>=0.3.0
yt-dlp==2024.12.13
python-dotenv==1.0.1
pytest==8.3.4
pytest-asyncio==0.24.0
httpx==0.28.1
```

- [ ] **Step 2: state.py를 SubtitleAnalysisState로 교체**

```python
# engine/state.py
import operator
from typing import TypedDict, List, Dict, Annotated
from enum import Enum


class UIAction(str, Enum):
    SUBTITLES = "subtitles"
    PROGRESS = "progress"
    CHUNK_SUMMARY = "chunk_summary"
    FINAL_SUMMARY = "final_summary"
    INSIGHTS = "insights"
    ERROR = "error"
    COMPLETE = "complete"


class SubtitleAnalysisState(TypedDict):
    # Input
    url: str
    is_live: bool

    # Extracted subtitles
    raw_subtitles: Annotated[List[Dict], operator.add]  # [{start, end, text}]

    # Chunked data
    chunks: Annotated[List[str], operator.add]

    # Summaries
    chunk_summaries: Annotated[List[str], operator.add]
    final_summary: str
    insights: str

    # Progress & UI
    progress: float
    ui_events: Annotated[List[Dict], operator.add]  # 노드 간 누적
```

- [ ] **Step 3: 의존성 설치**

Run: `cd /Users/lucy/Documents/ai-agent\ master/live-trans/backend && pip install -r requirements.txt`

- [ ] **Step 4: Commit**

```bash
git add backend/requirements.txt backend/engine/state.py
git commit -m "refactor: update deps and replace state with SubtitleAnalysisState"
```

---

### Task 2: 자막 추출 노드 (subtitle_extractor)

**Files:**
- Create: `backend/engine/nodes/subtitle_extractor.py`
- Create: `backend/tests/test_subtitle_extractor.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_subtitle_extractor.py
import pytest
from unittest.mock import patch, AsyncMock
from engine.nodes.subtitle_extractor import extract_subtitles_sync, subtitle_extractor_node


def test_parse_vtt_content():
    """VTT 자막 파싱이 올바르게 동작하는지 테스트"""
    from engine.nodes.subtitle_extractor import parse_vtt

    vtt_content = """WEBVTT

00:00:01.000 --> 00:00:04.000
안녕하세요 여러분

00:00:04.000 --> 00:00:08.000
오늘은 AI에 대해 이야기하겠습니다

00:00:08.000 --> 00:00:12.000
먼저 기본 개념부터 살펴보겠습니다
"""
    result = parse_vtt(vtt_content)
    assert len(result) == 3
    assert result[0]["text"] == "안녕하세요 여러분"
    assert result[0]["start"] == 1.0
    assert result[0]["end"] == 4.0
    assert result[1]["text"] == "오늘은 AI에 대해 이야기하겠습니다"


def test_parse_vtt_deduplicates():
    """중복 자막 라인 제거 테스트"""
    from engine.nodes.subtitle_extractor import parse_vtt

    vtt_content = """WEBVTT

00:00:01.000 --> 00:00:04.000
안녕하세요 여러분

00:00:02.000 --> 00:00:05.000
안녕하세요 여러분

00:00:04.000 --> 00:00:08.000
오늘은 AI에 대해 이야기하겠습니다
"""
    result = parse_vtt(vtt_content)
    assert len(result) == 2


def test_subtitle_extractor_node_sets_state():
    """노드가 state를 올바르게 업데이트하는지 테스트"""
    mock_subtitles = [
        {"start": 0.0, "end": 3.0, "text": "테스트 자막"},
    ]
    with patch(
        "engine.nodes.subtitle_extractor.extract_subtitles_sync",
        return_value=mock_subtitles,
    ):
        state = {
            "url": "https://youtube.com/watch?v=test123",
            "is_live": False,
            "raw_subtitles": [],
            "chunks": [],
            "chunk_summaries": [],
            "final_summary": "",
            "insights": "",
            "progress": 0.0,
            "ui_events": [],
        }
        result = subtitle_extractor_node(state)
        assert len(result["raw_subtitles"]) == 1
        assert result["raw_subtitles"][0]["text"] == "테스트 자막"
        assert result["progress"] == 0.1
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd /Users/lucy/Documents/ai-agent\ master/live-trans/backend && python -m pytest tests/test_subtitle_extractor.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: subtitle_extractor 구현**

```python
# engine/nodes/subtitle_extractor.py
import re
import subprocess
import shutil
import sys
import logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


def parse_vtt(vtt_content: str) -> List[Dict]:
    """VTT 자막 텍스트를 파싱하여 [{start, end, text}] 리스트로 변환"""
    lines = vtt_content.strip().split("\n")
    subtitles = []
    seen_texts = set()
    timestamp_re = re.compile(
        r"(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})"
    )

    i = 0
    while i < len(lines):
        match = timestamp_re.match(lines[i])
        if match:
            start = _ts_to_seconds(match.group(1))
            end = _ts_to_seconds(match.group(2))
            i += 1
            text_lines = []
            while i < len(lines) and lines[i].strip() and not timestamp_re.match(lines[i]):
                # Strip VTT tags like <c>, </c>, etc.
                clean = re.sub(r"<[^>]+>", "", lines[i].strip())
                if clean:
                    text_lines.append(clean)
                i += 1
            text = " ".join(text_lines)
            if text and text not in seen_texts:
                seen_texts.add(text)
                subtitles.append({"start": start, "end": end, "text": text})
        else:
            i += 1

    return subtitles


def _ts_to_seconds(ts: str) -> float:
    """HH:MM:SS.mmm → seconds"""
    h, m, rest = ts.split(":")
    s, ms = rest.split(".")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def extract_subtitles_sync(url: str) -> List[Dict]:
    """yt-dlp로 YouTube 한국어 자동번역 자막 추출"""
    yt_dlp_bin = shutil.which("yt-dlp") or str(Path(sys.executable).parent / "yt-dlp")

    # 한국어 자동번역 자막 다운로드
    result = subprocess.run(
        [
            yt_dlp_bin,
            "--write-auto-sub",
            "--sub-lang", "ko",
            "--sub-format", "vtt",
            "--skip-download",
            "--print", "subtitle:ko:filepath",
            "-o", "/tmp/yt-subs-%(id)s.%(ext)s",
            url,
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )

    subtitle_path = result.stdout.strip()
    if not subtitle_path or not Path(subtitle_path).exists():
        # 자동번역 자막이 없으면 원본 자막 시도
        result = subprocess.run(
            [
                yt_dlp_bin,
                "--write-sub",
                "--sub-lang", "ko",
                "--sub-format", "vtt",
                "--skip-download",
                "--print", "subtitle:ko:filepath",
                "-o", "/tmp/yt-subs-%(id)s.%(ext)s",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        subtitle_path = result.stdout.strip()

    if not subtitle_path or not Path(subtitle_path).exists():
        raise RuntimeError(f"자막을 찾을 수 없습니다: {url}")

    vtt_content = Path(subtitle_path).read_text(encoding="utf-8")
    subtitles = parse_vtt(vtt_content)

    # 임시 파일 정리
    try:
        Path(subtitle_path).unlink()
    except OSError:
        pass

    logger.info(f"Extracted {len(subtitles)} subtitle entries from {url}")
    return subtitles


def subtitle_extractor_node(state: Dict) -> Dict:
    """LangGraph 노드: YouTube 자막 추출"""
    url = state["url"]
    subtitles = extract_subtitles_sync(url)

    return {
        "raw_subtitles": subtitles,
        "progress": 0.1,
        "ui_events": [
            {
                "action": "subtitles",
                "data": {"subtitles": subtitles, "total": len(subtitles)},
            },
            {
                "action": "progress",
                "data": {"phase": "extracting", "progress": 0.1},
            },
        ],
    }
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd /Users/lucy/Documents/ai-agent\ master/live-trans/backend && python -m pytest tests/test_subtitle_extractor.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add backend/engine/nodes/subtitle_extractor.py backend/tests/test_subtitle_extractor.py
git commit -m "feat: add subtitle extractor node with VTT parsing"
```

---

### Task 3: 청크 분할 노드 (chunk_splitter)

**Files:**
- Create: `backend/engine/nodes/chunk_splitter.py`
- Create: `backend/tests/test_chunk_splitter.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_chunk_splitter.py
from engine.nodes.chunk_splitter import chunk_splitter_node


def test_splits_by_time_window():
    """5분 단위로 청크가 분할되는지 테스트"""
    subtitles = [
        {"start": 0.0, "end": 10.0, "text": f"문장 {i}"}
        for i in range(60)
    ]
    # 각 자막이 10초씩이면 60개 = 600초 = 10분 → 2개 청크
    for i, s in enumerate(subtitles):
        s["start"] = i * 10.0
        s["end"] = (i + 1) * 10.0

    state = {
        "raw_subtitles": subtitles,
        "chunks": [],
        "ui_events": [],
        "progress": 0.1,
    }
    result = chunk_splitter_node(state)
    assert len(result["chunks"]) == 2
    assert "문장 0" in result["chunks"][0]
    assert "문장 30" in result["chunks"][1]


def test_single_chunk_for_short_video():
    """5분 미만 영상은 1개 청크"""
    subtitles = [
        {"start": i * 5.0, "end": (i + 1) * 5.0, "text": f"짧은 문장 {i}"}
        for i in range(10)
    ]
    state = {
        "raw_subtitles": subtitles,
        "chunks": [],
        "ui_events": [],
        "progress": 0.1,
    }
    result = chunk_splitter_node(state)
    assert len(result["chunks"]) == 1


def test_empty_subtitles():
    """빈 자막이면 빈 청크"""
    state = {
        "raw_subtitles": [],
        "chunks": [],
        "ui_events": [],
        "progress": 0.1,
    }
    result = chunk_splitter_node(state)
    assert result["chunks"] == []
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd /Users/lucy/Documents/ai-agent\ master/live-trans/backend && python -m pytest tests/test_chunk_splitter.py -v`
Expected: FAIL

- [ ] **Step 3: chunk_splitter 구현**

```python
# engine/nodes/chunk_splitter.py
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

CHUNK_DURATION_SECONDS = 300  # 5분


def chunk_splitter_node(state: Dict) -> Dict:
    """LangGraph 노드: 자막을 5분 단위 청크로 분할"""
    subtitles = state.get("raw_subtitles", [])

    if not subtitles:
        return {"chunks": [], "progress": 0.2, "ui_events": []}

    chunks = []
    current_chunk_texts: List[str] = []
    chunk_start_time = subtitles[0]["start"]

    for sub in subtitles:
        if sub["start"] - chunk_start_time >= CHUNK_DURATION_SECONDS and current_chunk_texts:
            chunks.append("\n".join(current_chunk_texts))
            current_chunk_texts = []
            chunk_start_time = sub["start"]
        current_chunk_texts.append(sub["text"])

    # 마지막 청크
    if current_chunk_texts:
        chunks.append("\n".join(current_chunk_texts))

    logger.info(f"Split {len(subtitles)} subtitles into {len(chunks)} chunks")

    return {
        "chunks": chunks,
        "progress": 0.2,
        "ui_events": [
            {
                "action": "progress",
                "data": {
                    "phase": "summarizing",
                    "progress": 0.2,
                    "total_chunks": len(chunks),
                },
            }
        ],
    }
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd /Users/lucy/Documents/ai-agent\ master/live-trans/backend && python -m pytest tests/test_chunk_splitter.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add backend/engine/nodes/chunk_splitter.py backend/tests/test_chunk_splitter.py
git commit -m "feat: add chunk splitter node with 5-min time windows"
```

---

### Task 4: 청크 요약 노드 (chunk_summarizer)

**Files:**
- Create: `backend/engine/nodes/chunk_summarizer.py`
- Create: `backend/tests/test_chunk_summarizer.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_chunk_summarizer.py
from unittest.mock import patch, MagicMock
from engine.nodes.chunk_summarizer import chunk_summarizer_node


def _mock_claude_response(content: str):
    mock = MagicMock()
    mock.content = content
    return mock


def test_summarizes_all_chunks():
    """모든 청크가 요약되는지 테스트"""
    state = {
        "chunks": ["청크1 내용", "청크2 내용"],
        "chunk_summaries": [],
        "ui_events": [],
        "progress": 0.2,
    }

    with patch("engine.nodes.chunk_summarizer._get_llm") as mock_get:
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = [
            _mock_claude_response("청크1 요약입니다"),
            _mock_claude_response("청크2 요약입니다"),
        ]
        mock_get.return_value = mock_llm
        result = chunk_summarizer_node(state)

    assert len(result["chunk_summaries"]) == 2
    assert result["chunk_summaries"][0] == "청크1 요약입니다"
    assert result["chunk_summaries"][1] == "청크2 요약입니다"


def test_empty_chunks():
    """빈 청크 리스트면 빈 결과"""
    state = {
        "chunks": [],
        "chunk_summaries": [],
        "ui_events": [],
        "progress": 0.2,
    }
    result = chunk_summarizer_node(state)
    assert result["chunk_summaries"] == []


def test_emits_progress_events():
    """청크 처리마다 progress 이벤트가 발행되는지 테스트"""
    state = {
        "chunks": ["청크1", "청크2", "청크3"],
        "chunk_summaries": [],
        "ui_events": [],
        "progress": 0.2,
    }

    with patch("engine.nodes.chunk_summarizer._get_llm") as mock_get:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _mock_claude_response("요약")
        mock_get.return_value = mock_llm
        result = chunk_summarizer_node(state)

    chunk_summary_events = [
        e for e in result["ui_events"] if e["action"] == "chunk_summary"
    ]
    assert len(chunk_summary_events) == 3
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd /Users/lucy/Documents/ai-agent\ master/live-trans/backend && python -m pytest tests/test_chunk_summarizer.py -v`
Expected: FAIL

- [ ] **Step 3: chunk_summarizer 구현**

```python
# engine/nodes/chunk_summarizer.py
import os
import logging
from typing import Dict

logger = logging.getLogger(__name__)

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        from langchain_anthropic import ChatAnthropic
        _llm = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            max_tokens=2048,
        )
    return _llm

CHUNK_SUMMARY_PROMPT = """아래는 YouTube 영상의 한국어 자막 일부입니다.

이 내용의 핵심을 맥락에 맞게 요약해주세요.
- 주요 논점과 핵심 내용을 빠짐없이 포함
- 전문 용어가 있으면 그대로 유지
- 간결하되 중요한 세부사항은 보존

---
{chunk}
---

요약:"""


def chunk_summarizer_node(state: Dict) -> Dict:
    """LangGraph 노드: 각 청크를 Claude로 요약"""
    chunks = state.get("chunks", [])

    if not chunks:
        return {"chunk_summaries": [], "ui_events": [], "progress": 0.5}

    summaries = []
    ui_events = []

    for i, chunk in enumerate(chunks):
        prompt = CHUNK_SUMMARY_PROMPT.format(chunk=chunk)
        response = _get_llm().invoke(prompt)
        summary = response.content.strip() if hasattr(response, "content") else str(response)
        summaries.append(summary)

        progress = 0.2 + (0.5 * (i + 1) / len(chunks))
        ui_events.append({
            "action": "chunk_summary",
            "data": {"index": i, "summary": summary},
        })
        ui_events.append({
            "action": "progress",
            "data": {
                "phase": "summarizing",
                "progress": round(progress, 2),
                "chunk_index": i,
                "total_chunks": len(chunks),
            },
        })

        logger.info(f"Summarized chunk {i + 1}/{len(chunks)}")

    return {
        "chunk_summaries": summaries,
        "progress": 0.7,
        "ui_events": ui_events,
    }
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd /Users/lucy/Documents/ai-agent\ master/live-trans/backend && python -m pytest tests/test_chunk_summarizer.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add backend/engine/nodes/chunk_summarizer.py backend/tests/test_chunk_summarizer.py
git commit -m "feat: add chunk summarizer node using Claude"
```

---

### Task 5: 통합 요약 노드 (final_summarizer)

**Files:**
- Create: `backend/engine/nodes/final_summarizer.py`
- Create: `backend/tests/test_final_summarizer.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_final_summarizer.py
from unittest.mock import patch, MagicMock
from engine.nodes.final_summarizer import final_summarizer_node


def _mock_response(content):
    mock = MagicMock()
    mock.content = content
    return mock


def test_generates_final_summary():
    state = {
        "chunk_summaries": ["파트1 요약", "파트2 요약"],
        "final_summary": "",
        "ui_events": [],
        "progress": 0.7,
    }
    with patch("engine.nodes.final_summarizer._get_llm") as mock_get:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _mock_response("통합 요약 결과")
        mock_get.return_value = mock_llm
        result = final_summarizer_node(state)

    assert result["final_summary"] == "통합 요약 결과"
    assert any(e["action"] == "final_summary" for e in result["ui_events"])


def test_empty_summaries():
    state = {
        "chunk_summaries": [],
        "final_summary": "",
        "ui_events": [],
        "progress": 0.7,
    }
    result = final_summarizer_node(state)
    assert result["final_summary"] == ""
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd /Users/lucy/Documents/ai-agent\ master/live-trans/backend && python -m pytest tests/test_final_summarizer.py -v`
Expected: FAIL

- [ ] **Step 3: 구현**

```python
# engine/nodes/final_summarizer.py
import os
import logging
from typing import Dict

logger = logging.getLogger(__name__)

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        from langchain_anthropic import ChatAnthropic
        _llm = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            max_tokens=4096,
        )
    return _llm

FINAL_SUMMARY_PROMPT = """아래는 YouTube 영상의 각 파트별 요약입니다.

{chunk_summaries}

위 내용을 바탕으로 영상 전체의 통합 요약을 작성해주세요:
- 전체 흐름과 맥락을 반영한 구조화된 요약
- 주제별로 그루핑하여 정리
- 핵심 논점과 결론을 명확히
- 마크다운 형식으로 작성"""


def final_summarizer_node(state: Dict) -> Dict:
    """LangGraph 노드: 청크 요약들을 통합하여 최종 요약 생성"""
    chunk_summaries = state.get("chunk_summaries", [])

    if not chunk_summaries:
        return {"final_summary": "", "ui_events": [], "progress": 0.85}

    numbered = "\n\n".join(
        f"### 파트 {i + 1}\n{s}" for i, s in enumerate(chunk_summaries)
    )
    prompt = FINAL_SUMMARY_PROMPT.format(chunk_summaries=numbered)
    response = _get_llm().invoke(prompt)
    summary = response.content.strip() if hasattr(response, "content") else str(response)

    logger.info("Generated final summary")

    return {
        "final_summary": summary,
        "progress": 0.85,
        "ui_events": [
            {"action": "final_summary", "data": {"summary": summary}},
            {"action": "progress", "data": {"phase": "finalizing", "progress": 0.85}},
        ],
    }
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd /Users/lucy/Documents/ai-agent\ master/live-trans/backend && python -m pytest tests/test_final_summarizer.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add backend/engine/nodes/final_summarizer.py backend/tests/test_final_summarizer.py
git commit -m "feat: add final summarizer node for integrated summary"
```

---

### Task 6: 인사이트 생성 노드 (insight_generator)

**Files:**
- Create: `backend/engine/nodes/insight_generator.py`
- Create: `backend/tests/test_insight_generator.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_insight_generator.py
from unittest.mock import patch, MagicMock
from engine.nodes.insight_generator import insight_generator_node


def _mock_response(content):
    mock = MagicMock()
    mock.content = content
    return mock


def test_generates_insights():
    state = {
        "final_summary": "AI 기술의 발전과 활용에 대한 요약",
        "insights": "",
        "ui_events": [],
        "progress": 0.85,
    }
    with patch("engine.nodes.insight_generator._get_llm") as mock_get:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _mock_response("## 핵심 시사점\n- 포인트1")
        mock_get.return_value = mock_llm
        result = insight_generator_node(state)

    assert "핵심 시사점" in result["insights"]
    assert result["progress"] == 1.0
    assert any(e["action"] == "insights" for e in result["ui_events"])
    assert any(e["action"] == "complete" for e in result["ui_events"])


def test_empty_summary():
    state = {
        "final_summary": "",
        "insights": "",
        "ui_events": [],
        "progress": 0.85,
    }
    result = insight_generator_node(state)
    assert result["insights"] == ""
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd /Users/lucy/Documents/ai-agent\ master/live-trans/backend && python -m pytest tests/test_insight_generator.py -v`
Expected: FAIL

- [ ] **Step 3: 구현**

```python
# engine/nodes/insight_generator.py
import os
import logging
from typing import Dict

logger = logging.getLogger(__name__)

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        from langchain_anthropic import ChatAnthropic
        _llm = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            max_tokens=4096,
        )
    return _llm

INSIGHT_PROMPT = """아래는 YouTube 영상의 통합 요약입니다.

{final_summary}

이 내용을 바탕으로 다음 세 가지를 마크다운 형식으로 작성해주세요:

## 핵심 시사점
- 이 영상에서 가장 중요한 포인트 3~5가지

## 향후 전망 및 트렌드
- 이 내용이 시사하는 미래 방향성과 트렌드

## 액션 아이템
- 시청자가 이 내용을 바탕으로 실행할 수 있는 구체적 행동 제안"""


def insight_generator_node(state: Dict) -> Dict:
    """LangGraph 노드: 통합 요약 기반 인사이트 생성"""
    final_summary = state.get("final_summary", "")

    if not final_summary:
        return {"insights": "", "ui_events": [], "progress": 1.0}

    prompt = INSIGHT_PROMPT.format(final_summary=final_summary)
    response = _get_llm().invoke(prompt)
    insights = response.content.strip() if hasattr(response, "content") else str(response)

    logger.info("Generated insights")

    return {
        "insights": insights,
        "progress": 1.0,
        "ui_events": [
            {"action": "insights", "data": {"insights": insights}},
            {"action": "progress", "data": {"phase": "complete", "progress": 1.0}},
            {"action": "complete", "data": {}},
        ],
    }
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd /Users/lucy/Documents/ai-agent\ master/live-trans/backend && python -m pytest tests/test_insight_generator.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add backend/engine/nodes/insight_generator.py backend/tests/test_insight_generator.py
git commit -m "feat: add insight generator node"
```

---

### Task 7: LangGraph 그래프 재구성

**Files:**
- Modify: `backend/engine/graph.py`
- Create: `backend/tests/test_new_graph.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_new_graph.py
from engine.graph import build_graph


def test_graph_builds():
    """그래프가 정상적으로 빌드되는지 테스트"""
    graph = build_graph()
    assert graph is not None


def test_graph_has_correct_nodes():
    """그래프에 올바른 노드가 있는지 테스트"""
    graph = build_graph()
    node_names = set(graph.get_graph().nodes.keys())
    expected = {
        "__start__",
        "__end__",
        "subtitle_extractor",
        "chunk_splitter",
        "chunk_summarizer",
        "final_summarizer",
        "insight_generator",
    }
    assert expected.issubset(node_names)
```

- [ ] **Step 2: graph.py 교체**

```python
# engine/graph.py
from langgraph.graph import StateGraph, END
from engine.state import SubtitleAnalysisState
from engine.nodes.subtitle_extractor import subtitle_extractor_node
from engine.nodes.chunk_splitter import chunk_splitter_node
from engine.nodes.chunk_summarizer import chunk_summarizer_node
from engine.nodes.final_summarizer import final_summarizer_node
from engine.nodes.insight_generator import insight_generator_node


def build_graph():
    graph = StateGraph(SubtitleAnalysisState)

    graph.add_node("subtitle_extractor", subtitle_extractor_node)
    graph.add_node("chunk_splitter", chunk_splitter_node)
    graph.add_node("chunk_summarizer", chunk_summarizer_node)
    graph.add_node("final_summarizer", final_summarizer_node)
    graph.add_node("insight_generator", insight_generator_node)

    graph.set_entry_point("subtitle_extractor")
    graph.add_edge("subtitle_extractor", "chunk_splitter")
    graph.add_edge("chunk_splitter", "chunk_summarizer")
    graph.add_edge("chunk_summarizer", "final_summarizer")
    graph.add_edge("final_summarizer", "insight_generator")
    graph.add_edge("insight_generator", END)

    return graph.compile()
```

- [ ] **Step 3: 테스트 통과 확인**

Run: `cd /Users/lucy/Documents/ai-agent\ master/live-trans/backend && python -m pytest tests/test_new_graph.py -v`
Expected: 2 passed

- [ ] **Step 4: Commit**

```bash
git add backend/engine/graph.py backend/tests/test_new_graph.py
git commit -m "feat: rebuild LangGraph pipeline for subtitle analysis"
```

---

### Task 8: FastAPI 엔드포인트 업데이트

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: main.py 교체**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add backend/main.py
git commit -m "feat: update FastAPI endpoints for subtitle analysis pipeline"
```

---

### Task 9: 이전 노드 파일 삭제

**Files:**
- Delete: `backend/engine/nodes/stt_node.py`
- Delete: `backend/engine/nodes/translator.py`
- Delete: `backend/engine/nodes/summarizer.py`
- Delete: `backend/engine/nodes/fast_translator.py`
- Delete: `backend/engine/nodes/context_refiner.py`
- Delete: `backend/sources/base.py`
- Delete: `backend/sources/youtube.py`

- [ ] **Step 1: 불필요 파일 삭제**

```bash
rm backend/engine/nodes/stt_node.py
rm backend/engine/nodes/translator.py
rm backend/engine/nodes/summarizer.py
rm backend/engine/nodes/fast_translator.py
rm backend/engine/nodes/context_refiner.py
rm backend/sources/base.py
rm backend/sources/youtube.py
```

- [ ] **Step 2: 이전 테스트 중 깨지는 것 삭제**

```bash
rm backend/tests/test_stt_node.py
rm backend/tests/test_fast_translator.py
rm backend/tests/test_context_refiner.py
rm backend/tests/test_insight_extractor.py
rm backend/tests/test_youtube_source.py
rm backend/tests/test_graph.py
```

- [ ] **Step 3: Commit**

```bash
git add -u
git commit -m "chore: remove old STT/translation pipeline files"
```

---

## Chunk 2: 프론트엔드 업데이트

### Task 10: SSE 훅 업데이트

**Files:**
- Modify: `frontend/hooks/useSSE.ts`

- [ ] **Step 1: useSSE.ts 교체**

```typescript
"use client";

import { useState, useEffect, useCallback, useRef } from "react";

interface Subtitle {
  start: number;
  end: number;
  text: string;
}

interface SSEState {
  subtitles: Subtitle[];
  chunkSummaries: { index: number; summary: string }[];
  finalSummary: string;
  insights: string;
  progress: number;
  phase: string;
  isConnected: boolean;
  isComplete: boolean;
  error: string | null;
}

export function useSSE(url: string | null) {
  const [state, setState] = useState<SSEState>({
    subtitles: [],
    chunkSummaries: [],
    finalSummary: "",
    insights: "",
    progress: 0,
    phase: "",
    isConnected: false,
    isComplete: false,
    error: null,
  });

  const sourceRef = useRef<EventSource | null>(null);

  const disconnect = useCallback(() => {
    if (sourceRef.current) {
      sourceRef.current.close();
      sourceRef.current = null;
      setState((prev) => ({ ...prev, isConnected: false }));
    }
  }, []);

  useEffect(() => {
    if (!url) {
      disconnect();
      return;
    }

    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const source = new EventSource(
      `${backendUrl}/api/stream?url=${encodeURIComponent(url)}`
    );
    sourceRef.current = source;

    source.onopen = () => {
      setState((prev) => ({ ...prev, isConnected: true, error: null }));
    };

    source.addEventListener("subtitles", (e) => {
      const data = JSON.parse(e.data);
      setState((prev) => ({ ...prev, subtitles: data.subtitles }));
    });

    source.addEventListener("progress", (e) => {
      const data = JSON.parse(e.data);
      setState((prev) => ({
        ...prev,
        progress: data.progress,
        phase: data.phase,
      }));
    });

    source.addEventListener("chunk_summary", (e) => {
      const data = JSON.parse(e.data);
      setState((prev) => ({
        ...prev,
        chunkSummaries: [...prev.chunkSummaries, data],
      }));
    });

    source.addEventListener("final_summary", (e) => {
      const data = JSON.parse(e.data);
      setState((prev) => ({ ...prev, finalSummary: data.summary }));
    });

    source.addEventListener("insights", (e) => {
      const data = JSON.parse(e.data);
      setState((prev) => ({ ...prev, insights: data.insights }));
    });

    source.addEventListener("complete", () => {
      setState((prev) => ({ ...prev, isComplete: true, isConnected: false }));
      source.close();
    });

    source.addEventListener("error", (e) => {
      if (e instanceof MessageEvent) {
        const data = JSON.parse(e.data);
        setState((prev) => ({ ...prev, error: data.message }));
      }
    });

    source.onerror = () => {
      setState((prev) => ({ ...prev, isConnected: false }));
    };

    return () => {
      source.close();
    };
  }, [url, disconnect]);

  return { ...state, disconnect };
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/hooks/useSSE.ts
git commit -m "feat: update SSE hook for subtitle analysis events"
```

---

### Task 11: InsightPanel 업데이트

**Files:**
- Modify: `frontend/components/InsightPanel.tsx`

- [ ] **Step 1: InsightPanel.tsx 교체**

```tsx
"use client";

interface Props {
  chunkSummaries: { index: number; summary: string }[];
  finalSummary: string;
  insights: string;
  progress: number;
  phase: string;
}

const PHASE_LABELS: Record<string, string> = {
  extracting: "자막 추출 중...",
  summarizing: "요약 생성 중...",
  finalizing: "통합 분석 중...",
  complete: "분석 완료",
};

export default function InsightPanel({
  chunkSummaries,
  finalSummary,
  insights,
  progress,
  phase,
}: Props) {
  return (
    <div className="bg-gray-800 rounded-lg p-4 h-full overflow-y-auto flex flex-col gap-4">
      {/* 진행률 */}
      {phase && phase !== "complete" && (
        <div>
          <div className="flex justify-between text-xs text-gray-400 mb-1">
            <span>{PHASE_LABELS[phase] || phase}</span>
            <span>{Math.round(progress * 100)}%</span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-2">
            <div
              className="bg-blue-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* 청크별 요약 */}
      {chunkSummaries.length > 0 && !finalSummary && (
        <div>
          <h2 className="text-sm font-semibold text-gray-400 mb-2 uppercase tracking-wide">
            파트별 요약
          </h2>
          <div className="space-y-2">
            {chunkSummaries.map((cs) => (
              <div key={cs.index} className="text-sm text-gray-300 border-l-2 border-blue-500 pl-3">
                <span className="text-blue-400 text-xs">파트 {cs.index + 1}</span>
                <p className="mt-1">{cs.summary}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 통합 요약 */}
      {finalSummary && (
        <div>
          <h2 className="text-sm font-semibold text-gray-400 mb-2 uppercase tracking-wide">
            통합 요약
          </h2>
          <div className="text-sm text-gray-300 whitespace-pre-wrap">{finalSummary}</div>
        </div>
      )}

      {/* 인사이트 */}
      {insights && (
        <div>
          <h2 className="text-sm font-semibold text-blue-400 mb-2 uppercase tracking-wide">
            인사이트
          </h2>
          <div className="text-sm text-gray-300 whitespace-pre-wrap">{insights}</div>
        </div>
      )}

      {/* 대기 상태 */}
      {!phase && chunkSummaries.length === 0 && (
        <p className="text-gray-500 text-sm">URL을 입력하면 분석이 시작됩니다</p>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/InsightPanel.tsx
git commit -m "feat: update InsightPanel with progress bar, summary, and insights sections"
```

---

### Task 12: ControlBar 업데이트

**Files:**
- Modify: `frontend/components/ControlBar.tsx`

- [ ] **Step 1: ControlBar.tsx 교체**

```tsx
"use client";

interface Props {
  isConnected: boolean;
  isComplete: boolean;
  onStop: () => void;
  onSummarizeNow: () => void;
  finalSummary: string;
  insights: string;
}

export default function ControlBar({
  isConnected,
  isComplete,
  onStop,
  onSummarizeNow,
  finalSummary,
  insights,
}: Props) {
  const handleExportMarkdown = () => {
    let md = `# 영상 분석 노트\n\n`;
    md += `**분석일:** ${new Date().toISOString().split("T")[0]}\n\n---\n\n`;
    if (finalSummary) {
      md += `## 통합 요약\n\n${finalSummary}\n\n---\n\n`;
    }
    if (insights) {
      md += `${insights}\n\n`;
    }

    const blob = new Blob([md], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `analysis-${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex items-center justify-between px-4 py-3 bg-gray-800 rounded-lg">
      <div className="flex items-center gap-2">
        <div
          className={`w-2 h-2 rounded-full ${
            isConnected ? "bg-green-400 animate-pulse" : isComplete ? "bg-blue-400" : "bg-gray-500"
          }`}
        />
        <span className="text-sm text-gray-400">
          {isConnected ? "분석 중" : isComplete ? "분석 완료" : "대기 중"}
        </span>
      </div>
      <div className="flex gap-2">
        {isConnected && (
          <>
            <button
              onClick={onSummarizeNow}
              className="px-4 py-1.5 bg-blue-600 rounded text-sm hover:bg-blue-500"
            >
              지금 요약
            </button>
            <button
              onClick={onStop}
              className="px-4 py-1.5 bg-red-600 rounded text-sm hover:bg-red-500"
            >
              정지
            </button>
          </>
        )}
        {(isComplete || finalSummary) && (
          <button
            onClick={handleExportMarkdown}
            className="px-4 py-1.5 bg-gray-600 rounded text-sm hover:bg-gray-500"
          >
            내보내기 (MD)
          </button>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/ControlBar.tsx
git commit -m "feat: update ControlBar with summarize-now button and simplified export"
```

---

### Task 13: 메인 페이지 업데이트

**Files:**
- Modify: `frontend/app/page.tsx`
- Delete: `frontend/components/GlossaryPanel.tsx`

- [ ] **Step 1: page.tsx 교체**

```tsx
"use client";

import { useState } from "react";
import { useSSE } from "@/hooks/useSSE";
import SourceInput from "@/components/SourceInput";
import InsightPanel from "@/components/InsightPanel";
import ControlBar from "@/components/ControlBar";

function extractYouTubeId(url: string): string | null {
  const patterns = [
    /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/,
    /youtube\.com\/live\/([a-zA-Z0-9_-]{11})/,
  ];
  for (const p of patterns) {
    const m = url.match(p);
    if (m) return m[1];
  }
  return null;
}

export default function Home() {
  const [activeUrl, setActiveUrl] = useState<string | null>(null);

  const {
    subtitles,
    chunkSummaries,
    finalSummary,
    insights,
    progress,
    phase,
    isConnected,
    isComplete,
    disconnect,
  } = useSSE(activeUrl);

  const videoId = activeUrl ? extractYouTubeId(activeUrl) : null;

  const handleStart = (url: string) => setActiveUrl(url);

  const handleStop = async () => {
    if (activeUrl) {
      const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      await fetch(`${backendUrl}/api/stop?url=${encodeURIComponent(activeUrl)}`, {
        method: "POST",
      });
    }
    disconnect();
    setActiveUrl(null);
  };

  const handleSummarizeNow = async () => {
    if (activeUrl) {
      const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      await fetch(
        `${backendUrl}/api/summarize-now?url=${encodeURIComponent(activeUrl)}`,
        { method: "POST" }
      );
    }
  };

  return (
    <main className="h-screen flex flex-col p-4 gap-4">
      <div className="flex items-center gap-4">
        <h1 className="text-xl font-bold shrink-0">Live-Trans</h1>
        <SourceInput onSubmit={handleStart} disabled={isConnected} />
      </div>

      <div className="flex-1 flex gap-4 min-h-0">
        {/* 영상 영역 */}
        <div className="flex-1 relative bg-gray-800 rounded-lg flex items-center justify-center overflow-hidden">
          {!activeUrl && (
            <p className="text-gray-500">YouTube URL을 입력하여 시작하세요</p>
          )}
          {videoId && (
            <iframe
              className="absolute inset-0 w-full h-full"
              src={`https://www.youtube.com/embed/${videoId}?autoplay=1`}
              allow="autoplay; encrypted-media; fullscreen"
              allowFullScreen
            />
          )}
          {activeUrl && !videoId && (
            <p className="text-gray-400 text-sm">자막 추출 중...</p>
          )}
        </div>

        {/* 분석 패널 */}
        <div className="w-96 flex flex-col gap-4">
          <div className="flex-1 min-h-0">
            <InsightPanel
              chunkSummaries={chunkSummaries}
              finalSummary={finalSummary}
              insights={insights}
              progress={progress}
              phase={phase}
            />
          </div>
        </div>
      </div>

      <ControlBar
        isConnected={isConnected}
        isComplete={isComplete}
        onStop={handleStop}
        onSummarizeNow={handleSummarizeNow}
        finalSummary={finalSummary}
        insights={insights}
      />
    </main>
  );
}
```

- [ ] **Step 2: GlossaryPanel 삭제**

```bash
rm frontend/components/GlossaryPanel.tsx
```

- [ ] **Step 3: SubtitleDisplay.tsx는 유지하되 사용하지 않음 (추후 필요시 활용)**

- [ ] **Step 4: Commit**

```bash
git add frontend/app/page.tsx
git rm frontend/components/GlossaryPanel.tsx
git commit -m "feat: simplify main page UI for subtitle analysis workflow"
```

---

## Chunk 3: 통합 테스트 및 마무리

### Task 14: 환경 설정 업데이트

**Files:**
- Modify: `backend/.env.example` (or `.env`)

- [ ] **Step 1: .env.example 업데이트**

`.env.example`에 추가:
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

기존 `OPENAI_API_KEY`, `WHISPER_MODEL` 라인 제거.

- [ ] **Step 2: Commit**

```bash
git add backend/.env.example
git commit -m "chore: update env config for Anthropic API"
```

---

### Task 15: 전체 테스트 실행 및 정리

- [ ] **Step 1: 남은 테스트 파일 중 깨지는 것 확인 및 수정**

Run: `cd /Users/lucy/Documents/ai-agent\ master/live-trans/backend && python -m pytest tests/ -v --tb=short`

깨지는 테스트(`test_state.py`, `test_api.py`)가 있으면 새 State/API에 맞게 수정.

- [ ] **Step 2: test_state.py 업데이트 (필요시)**

새 `SubtitleAnalysisState`에 맞게 테스트 수정.

- [ ] **Step 3: test_api.py 업데이트 (필요시)**

새 API 엔드포인트에 맞게 테스트 수정.

- [ ] **Step 4: 전체 테스트 통과 확인**

Run: `cd /Users/lucy/Documents/ai-agent\ master/live-trans/backend && python -m pytest tests/ -v`
Expected: All passed

- [ ] **Step 5: Final Commit**

```bash
git add -A
git commit -m "test: update tests for new subtitle analysis pipeline"
```
