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
