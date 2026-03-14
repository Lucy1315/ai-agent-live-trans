import asyncio
import shutil
import subprocess
import sys
from pathlib import Path
from typing import AsyncGenerator
from sources.base import AudioSource


def _resolve_bin(name: str) -> str:
    """Resolve binary path, falling back to the venv's bin directory."""
    return shutil.which(name) or str(Path(sys.executable).parent / name)


class YouTubeSource(AudioSource):
    """Extract audio from YouTube live/recorded streams using yt-dlp."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._yt_proc = None
        self._ff_proc = None

    async def stream_chunks(self, url: str) -> AsyncGenerator[bytes, None]:
        chunk_samples = int(self.chunk_duration * self.sample_rate)
        overlap_samples = int(self.overlap * self.sample_rate)
        step_samples = chunk_samples - overlap_samples

        cmd = [
            _resolve_bin("yt-dlp"), "-f", "bestaudio", "-o", "-", url,
            "--quiet", "--no-warnings",
        ]
        ffmpeg_cmd = [
            _resolve_bin("ffmpeg"), "-i", "pipe:0",
            "-f", "s16le", "-acodec", "pcm_s16le",
            "-ar", str(self.sample_rate), "-ac", "1",
            "-loglevel", "error",
            "pipe:1",
        ]

        # Use subprocess.Popen for native pipe chaining (yt-dlp | ffmpeg)
        self._yt_proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        self._ff_proc = subprocess.Popen(
            ffmpeg_cmd, stdin=self._yt_proc.stdout,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        # Allow yt_proc to receive SIGPIPE if ff_proc exits
        self._yt_proc.stdout.close()

        loop = asyncio.get_event_loop()
        buffer = b""
        bytes_per_chunk = chunk_samples * 2  # int16 = 2 bytes
        bytes_per_step = step_samples * 2

        try:
            while True:
                data = await loop.run_in_executor(
                    None, self._ff_proc.stdout.read, 4096
                )
                if not data:
                    break
                buffer += data
                while len(buffer) >= bytes_per_chunk:
                    yield buffer[:bytes_per_chunk]
                    buffer = buffer[bytes_per_step:]
        finally:
            await self.close()

        if buffer:
            yield buffer

    async def close(self):
        for proc in (self._ff_proc, self._yt_proc):
            if proc and proc.poll() is None:
                try:
                    proc.kill()
                    proc.wait()
                except (ProcessLookupError, OSError):
                    pass
        self._yt_proc = None
        self._ff_proc = None
