from abc import ABC, abstractmethod
from typing import AsyncGenerator


class AudioSource(ABC):
    def __init__(self, chunk_duration: float = 2.0, overlap: float = 0.5,
                 sample_rate: int = 16000):
        self.chunk_duration = chunk_duration
        self.overlap = overlap
        self.sample_rate = sample_rate

    @abstractmethod
    async def stream_chunks(self, url: str) -> AsyncGenerator[bytes, None]:
        """Yield PCM audio chunks (16kHz mono int16)."""
        ...

    async def close(self):
        """Release resources."""
        pass
