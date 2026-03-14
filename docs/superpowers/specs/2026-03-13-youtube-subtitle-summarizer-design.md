# YouTube 자막 기반 요약/인사이트 LangGraph 에이전트

## 배경

기존 시스템은 Audio → Whisper STT → GPT 번역 → 요약 파이프라인으로 실시간 번역과 요약을 동시에 처리하여 품질이 저하됨. YouTube 자체 자동번역 기능을 활용하여 자막을 추출하고, 전체 맥락 기반의 고품질 요약 + 인사이트를 생성하는 방식으로 전환.

## 아키텍처

```
[YouTube URL 입력]
       ↓
[subtitle_extractor] ── yt-dlp로 한국어 자동번역 자막 추출
       ↓
[chunk_splitter] ── 시간/분량 기준으로 자막을 청크로 분할
       ↓
[chunk_summarizer] ── Claude로 각 청크 핵심 요약 (진행상황 SSE 전송)
       ↓
[final_summarizer] ── 전체 청크 요약을 통합, 맥락 기반 최종 요약
       ↓
[insight_generator] ── 핵심 시사점, 향후 전망, 액션 아이템 생성
       ↓
[결과 전송] ── SSE로 프론트엔드에 전달
```

## LangGraph 상태

```python
class SubtitleAnalysisState(TypedDict):
    url: str                          # YouTube URL
    is_live: bool                     # 라이브 여부
    raw_subtitles: list[dict]         # 추출된 자막 [{start, end, text}]
    chunks: list[str]                 # 분할된 청크
    chunk_summaries: list[str]        # 청크별 요약
    final_summary: str                # 통합 요약
    insights: str                     # 인사이트
    ui_events: list[dict]             # SSE 이벤트
    progress: float                   # 진행률 (0~1)
```

## 노드 설계

### 1. subtitle_extractor
- yt-dlp로 한국어 자동번역 자막(vtt) 추출
- 녹화 영상: 전체 자막 일괄 추출
- 라이브: 30초 간격 폴링으로 새 자막 수집
- LLM 불필요

### 2. chunk_splitter
- 자막을 5분 또는 50문장 단위로 청크 분할
- 타임스탬프 기반 분할로 맥락 유지
- LLM 불필요

### 3. chunk_summarizer
- Claude로 각 청크 핵심 내용 요약
- 청크 처리 시마다 SSE로 진행상황 전송
- 이전 청크 요약을 컨텍스트로 전달하여 맥락 연결

### 4. final_summarizer
- 모든 청크 요약을 종합하여 전체 흐름 기반 통합 요약
- 주제별 그루핑, 핵심 논점 정리

### 5. insight_generator
- 통합 요약 기반으로 인사이트 생성
- 핵심 시사점, 향후 전망/트렌드, 실행 가능한 액션 아이템

## 라이브 스트리밍 처리

- 라이브 감지 시 폴링 모드 전환 (30초 간격)
- 5분마다 자동 중간 요약 생성
- "지금 요약" 버튼으로 수동 트리거 가능
- 스트림 종료 시 최종 통합 요약 + 인사이트 자동 생성

## API 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `GET /api/stream` | GET | SSE 스트림 (url 파라미터만 필수) |
| `POST /api/summarize-now` | POST | 라이브 수동 요약 트리거 |
| `POST /api/stop` | POST | 세션 중지 |
| `GET /api/export/markdown` | GET | 마크다운 내보내기 |
| `GET /health` | GET | 헬스체크 |

## 프론트엔드 변경

### 제거
- Whisper 모델 선택
- GPT 모델 선택
- 도메인 선택
- 용어집(Glossary) 업로드

### 유지
- YouTube URL 입력
- 자막 표시 영역
- 요약 패널
- SSE 연결
- 내보내기 (JSON, Markdown)
- 연결 상태 표시

### 추가
- 진행률 표시바
- "지금 요약" 버튼
- 인사이트 전용 섹션 (시사점, 전망, 액션 아이템)

## 의존성 변경

### 추가
- `langchain-anthropic` — Claude LLM 연동

### 제거
- `faster-whisper` — STT 불필요
- `openai` — GPT 불필요
- `pysbd` — 문장 분리 불필요
- `argostranslate` — 오프라인 번역 불필요

### 유지
- `langgraph` — 에이전트 프레임워크
- `yt-dlp` — YouTube 자막 추출
- `fastapi` — API 서버
- `sse-starlette` — SSE 스트리밍
- `uvicorn` — ASGI 서버
- `python-dotenv` — 환경 설정

## SSE 이벤트

| 이벤트 | 데이터 |
|--------|--------|
| `subtitles` | `{subtitles: [{start, end, text}], total: N}` |
| `progress` | `{phase: "extracting"\|"summarizing"\|"finalizing", progress: 0~1, chunk_index: N}` |
| `chunk_summary` | `{index: N, summary: "..."}` |
| `final_summary` | `{summary: "..."}` |
| `insights` | `{insights: "..."}` |
| `error` | `{message: "..."}` |
| `complete` | `{}` |

## LLM 모델
- Claude (langchain-anthropic) — 요약 및 인사이트 생성 전용
- 환경변수: `ANTHROPIC_API_KEY`
