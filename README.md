# Live-Trans - 실시간 웨비나 통번역 시스템

YouTube 영상의 영어 발화를 실시간으로 한국어 번역하고, 핵심 용어를 추출하며, 인사이트 요약까지 자동 생성하는 AI 통번역 시스템입니다.

---

## 서비스 개요

```
┌─────────────────────────────────────────────────────────────────┐
│  브라우저 (localhost:3000)                                       │
│  ┌──────────────────────────┐  ┌──────────────┐                 │
│  │   YouTube 영상 임베드     │  │  용어 사전     │                 │
│  │                          │  │  AI, CDRH ... │                 │
│  │   ┌──────────────────┐   │  ├──────────────┤                 │
│  │   │ 한국어 자막 표시   │   │  │  실시간 요약   │                 │
│  │   │ (작게/표준/크게)  │   │  │  #1 ...       │                 │
│  │   └──────────────────┘   │  │  #2 ...       │                 │
│  └──────────────────────────┘  └──────────────┘                 │
│  ┌──────────────────────────────────────────────┐               │
│  │ ● 실시간 수신 중  [정지] [인사이트생성] [내보내기] │               │
│  └──────────────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

### 핵심 기능

| 기능 | 설명 |
|------|------|
| 실시간 자막 | 영어 음성 → Whisper STT → GPT-4o-mini 빠른 번역 → GPT-4o 정제 번역 |
| 용어 사전 | 전문 용어 자동 추출 및 한국어 정의 생성 |
| 실시간 요약 | 정제 번역 5문장마다 핵심 포인트 1개 자동 생성 |
| 최종 인사이트 | 세션 종료 후 통합 요약 + 핵심 시사점 + 전망 + 액션 아이템 |
| 내보내기 | Markdown / JSON 형식으로 분석 결과 다운로드 |
| 자막 크기 조절 | 작게 / 표준 / 크게 3단계 |

---

## 기술 스택

### Backend
- **FastAPI** + Uvicorn — API 서버
- **LangGraph** 0.2.60 — 번역 파이프라인 오케스트레이션
- **faster-whisper** — 음성 인식 (STT)
- **OpenAI GPT-4o** — 맥락 정제 번역 + 용어 추출
- **OpenAI GPT-4o-mini** — 빠른 번역 + 인사이트 추출
- **yt-dlp** + **ffmpeg** — YouTube 오디오 스트리밍
- **pysbd** — 영어 문장 경계 감지
- **SSE (sse-starlette)** — 실시간 이벤트 스트리밍

### Frontend
- **Next.js 14** (App Router) — React 프레임워크
- **TypeScript** — 타입 안전성
- **Tailwind CSS** — 스타일링
- **EventSource API** — SSE 클라이언트

---

## 아키텍처

```
YouTube URL
    │
    ▼
┌──────────┐     ┌──────────────┐     ┌─────────────────┐
│  yt-dlp  │────▶│    ffmpeg     │────▶│  Whisper (STT)  │
│ (오디오)  │     │ (PCM 16kHz)  │     │  영어 텍스트 출력 │
└──────────┘     └──────────────┘     └────────┬────────┘
                                               │
                                               ▼
                                    ┌─────────────────────┐
                                    │   LangGraph 파이프라인  │
                                    │                     │
                                    │  (상세 흐름은 아래)    │
                                    └──────────┬──────────┘
                                               │
                                          SSE Events
                                               │
                                               ▼
                                    ┌─────────────────────┐
                                    │   Next.js Frontend   │
                                    │  (EventSource 수신)   │
                                    └─────────────────────┘
```

---

## LangGraph 파이프라인

### 노드 구성

```
                    ┌───────────┐
                    │  stt_node │
                    └─────┬─────┘
                          │
                ┌─────────┴─────────┐
                │                   │
         is_sentence_end?      (아직 문장 미완성)
           = True                = False
                │                   │
                ▼                   ▼
        ┌──────────────┐    ┌────────────────┐
        │  both_tracks │    │ fast_translator │──▶ END
        │              │    │  (GPT-4o-mini)  │
        │ ┌──────────┐ │    └────────────────┘
        │ │fast_trans.│ │
        │ └──────────┘ │
        │ ┌──────────┐ │
        │ │ context   │ │
        │ │ _refiner  │ │
        │ │ (GPT-4o)  │ │
        │ └──────────┘ │
        └──────┬───────┘
               │
      refined_sentences
        % 5 == 0 ?
               │
        ┌──────┴──────┐
        │             │
       Yes           No
        │             │
        ▼             ▼
┌───────────────┐
│   insight     │──▶ END
│  _extractor   │
│ (GPT-4o-mini) │
└───────────────┘
```

### 노드별 역할

#### 1. `stt_node` — 문장 경계 감지
- Whisper가 출력한 영어 텍스트를 `sentence_buffer`에 누적
- **pysbd** 라이브러리로 문장 완성 여부 판단
- 슬라이딩 윈도우 오버랩에 의한 중복 텍스트 제거
- 완성된 문장은 `full_transcript`에 기록

#### 2. `fast_translator` — 빠른 번역 (GPT-4o-mini)
- 누적된 문장 버퍼 전체를 번역 (조각이 아닌 맥락 포함)
- 이전 3개 번역문 + 용어집을 맥락으로 제공
- 발표/웨비나 전문 통역 프롬프트 사용
- **SSE 이벤트**: `fast_subtitle`

#### 3. `context_refiner` — 정제 번역 (GPT-4o)
- 완성된 문장만 대상 (문장 경계 감지 후)
- 이전 5개 번역문 + 전체 용어집을 맥락으로 사용
- 새로운 전문 용어 자동 추출 → 용어 사전에 추가
- **SSE 이벤트**: `refined_subtitle`, `glossary`

#### 4. `insight_extractor` — 인사이트 추출 (GPT-4o-mini)
- 정제 번역 5문장 누적될 때마다 실행 (~30초 간격)
- 최근 5문장에서 핵심 포인트 1~2문장 요약
- **SSE 이벤트**: `summary`

### 상태 (WebinarState)

```python
class WebinarState(TypedDict):
    # 입력
    audio_source_url: str        # YouTube URL
    audio_chunk: bytes           # PCM 오디오 청크
    current_chunk_text: str      # Whisper STT 결과

    # 문장 경계 감지
    is_sentence_end: bool        # 문장 완성 여부
    sentence_buffer: str         # 누적 중인 문장
    chunk_id: int                # 청크 순번

    # 번역 결과
    fast_translation: str        # GPT-4o-mini 빠른 번역
    refined_translation: str     # GPT-4o 정제 번역
    refined_sentences: list      # 정제 번역 이력 (최근 20개)
    new_terms_found: bool        # 새 용어 발견 여부

    # 누적 데이터
    full_transcript: list        # 전체 영어 원문
    glossary_dict: dict          # 용어 사전 {영어: 한국어}
    summary_points: list         # 실시간 요약 포인트들

    # UI 이벤트 큐
    ui_events: list              # 프론트엔드로 전송할 SSE 이벤트
```

---

## SSE 이벤트 흐름

```
Backend                              Frontend
   │                                    │
   │──── fast_subtitle ────────────────▶│  자막 표시 (임시 번역)
   │     {text, chunk_id}               │
   │                                    │
   │──── refined_subtitle ─────────────▶│  자막 교체 (정제 번역, 페이드 애니메이션)
   │     {text, chunk_id}               │
   │                                    │
   │──── glossary ─────────────────────▶│  용어 사전 패널에 추가
   │     {term: definition}             │
   │                                    │
   │──── summary ──────────────────────▶│  실시간 요약 패널에 추가
   │     {point, index}                 │
   │                                    │
   │──── error ────────────────────────▶│  에러 표시
   │     {message}                      │
```

---

## 사용자 워크플로우

```
1. URL 입력          YouTube URL을 입력하고 [시작] 클릭
        │
        ▼
2. 실시간 수신        영상 시청 + 한국어 자막 + 용어 추출 + 요약 자동 생성
   (자막 크기 조절 가능: 작게/표준/크게)
        │
        ▼
3. 세션 종료          [정지] 버튼 클릭
        │
        ▼
4. 최종 인사이트      [최종 인사이트 생성] 버튼 클릭
   (GPT-4o가 생성)    ├── 통합 요약 (3~5문장)
                     ├── 핵심 시사점 (3~5가지)
                     ├── 향후 전망 (2~3가지)
                     └── 액션 아이템 (2~3가지)
        │
        ▼
5. 내보내기           [요약본 (MD)] 또는 [내보내기 (JSON)]
```

---

## 프로젝트 구조

```
live-trans/
├── backend/
│   ├── main.py                          # FastAPI 앱 + API 엔드포인트
│   ├── .env                             # 환경변수 (OPENAI_API_KEY, WHISPER_MODEL)
│   ├── requirements.txt                 # Python 의존성
│   ├── Dockerfile                       # 백엔드 Docker 이미지
│   ├── engine/
│   │   ├── state.py                     # WebinarState + UIAction 정의
│   │   ├── graph.py                     # LangGraph 파이프라인 구성
│   │   └── nodes/
│   │       ├── stt_node.py              # 문장 경계 감지
│   │       ├── fast_translator.py       # GPT-4o-mini 빠른 번역
│   │       ├── context_refiner.py       # GPT-4o 정제 번역 + 용어 추출
│   │       └── insight_extractor.py     # 실시간 요약 포인트 추출
│   ├── sources/
│   │   ├── base.py                      # AudioSource 추상 클래스
│   │   └── youtube.py                   # YouTube 오디오 스트리밍
│   ├── exports/                         # 세션 자동 저장 디렉토리
│   └── tests/                           # pytest 테스트
│       ├── test_stt_node.py
│       ├── test_fast_translator.py
│       ├── test_context_refiner.py
│       ├── test_insight_extractor.py
│       ├── test_graph.py
│       ├── test_youtube_source.py
│       ├── test_api.py
│       └── test_state.py
│
├── frontend/
│   ├── app/
│   │   ├── layout.tsx                   # 루트 레이아웃 (다크 테마)
│   │   ├── page.tsx                     # 메인 페이지 (YouTube 임베드 + 자막)
│   │   └── globals.css                  # 전역 스타일
│   ├── components/
│   │   ├── SourceInput.tsx              # URL 입력 폼
│   │   ├── SubtitleDisplay.tsx          # 자막 표시 + 크기 조절
│   │   ├── GlossaryPanel.tsx            # 용어 사전 패널
│   │   ├── InsightPanel.tsx             # 실시간 요약 + 최종 인사이트
│   │   └── ControlBar.tsx              # 제어 바 + 내보내기
│   ├── hooks/
│   │   └── useSSE.ts                    # SSE 이벤트 수신 훅
│   ├── lib/
│   │   └── types.ts                     # TypeScript 타입 정의
│   ├── next.config.js                   # API 프록시 설정
│   ├── package.json                     # Node.js 의존성
│   └── tsconfig.json                    # TypeScript 설정
│
├── docker-compose.yml                   # Docker Compose 설정
└── .env.example                         # 환경변수 템플릿
```

---

## API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| `GET` | `/health` | 서버 상태 확인 |
| `GET` | `/api/stream?url=` | SSE 스트림 시작 (실시간 번역) |
| `POST` | `/api/stop?url=` | 스트림 중단 |
| `POST` | `/api/final-summary?url=` | 최종 인사이트 요약 생성 (GPT-4o) |
| `GET` | `/api/export/markdown?url=` | 세션 데이터 마크다운 내보내기 |

---

## 실행 방법

### 로컬 실행

```bash
# 1. 백엔드
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # OPENAI_API_KEY 설정
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 2. 프론트엔드
cd frontend
npm install
npm run dev
```

### Docker 실행

```bash
docker compose up
```

### 필수 환경변수

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `OPENAI_API_KEY` | OpenAI API 키 | (필수) |
| `WHISPER_MODEL` | Whisper 모델 크기 (base/small/medium/large) | `small` |

---

## 오디오 처리 설정

| 항목 | 값 | 설명 |
|------|-----|------|
| 청크 크기 | 5초 | 한 번에 처리하는 오디오 길이 |
| 오버랩 | 1초 | 청크 간 겹침 (문맥 유지) |
| 샘플레이트 | 16kHz | Whisper 입력 규격 |
| 오디오 포맷 | PCM s16le mono | ffmpeg 출력 포맷 |

---

## 번역 품질 전략

### 이중 트랙 번역 (Dual-Track Translation)

```
영어 원문: "The CDRH colleagues really set the stage for policy development."

  Track 1 (빠른 번역, ~1초)
  └─ GPT-4o-mini: "CDRH의 동료들이 정책 개발을 위한 기반을 마련했습니다."
     → 즉시 자막 표시 ("임시 번역" 라벨)

  Track 2 (정제 번역, ~3초)
  └─ GPT-4o: "CDRH(의료기기방사선보건센터)의 동료들이 해당 분야의
              정책 개발을 위한 기틀을 마련했습니다."
     → 자막 교체 (페이드 애니메이션)
     → 용어 추출: CDRH → "FDA 산하 의료기기 규제 기관"
```

### 품질 향상 기법

1. **누적 문맥 번역** — 5초 조각이 아닌 누적된 문장 전체를 번역
2. **이전 번역 맥락** — 최근 3~5개 번역문을 컨텍스트로 제공
3. **용어 일관성** — 추출된 용어 사전을 매 번역에 참조
4. **문장 경계 감지** — pysbd로 완성된 문장만 정제 번역 대상
5. **중복 제거** — 오버랩 구간의 텍스트 중복 자동 제거
