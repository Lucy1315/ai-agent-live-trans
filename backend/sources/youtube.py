import asyncio
import subprocess
from typing import AsyncGenerator
from sources.base import AudioSource


class YouTubeSource(AudioSource):
    """Extract audio from YouTube live/recorded streams using yt-dlp."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._process = None

    async def stream_chunks(self, url: str) -> AsyncGenerator[bytes, None]:
        chunk_samples = int(self.chunk_duration * self.sample_rate)
        overlap_samples = int(self.overlap * self.sample_rate)
        step_samples = chunk_samples - overlap_samples

        cmd = [
            "yt-dlp", "-f", "bestaudio", "-o", "-", url,
            "--quiet", "--no-warnings",
        ]
        ffmpeg_cmd = [
            "ffmpeg", "-i", "pipe:0",
            "-f", "s16le", "-acodec", "pcm_s16le",
            "-ar", str(self.sample_rate), "-ac", "1",
            "pipe:1",
        ]

        yt_proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        ff_proc = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd, stdin=yt_proc.stdout,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        self._process = (yt_proc, ff_proc)

        buffer = b""
        bytes_per_chunk = chunk_samples * 2  # int16 = 2 bytes
        bytes_per_step = step_samples * 2

        try:
            while True:
                data = await ff_proc.stdout.read(4096)
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
        if self._process:
            for proc in self._process:
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
            self._process = None
