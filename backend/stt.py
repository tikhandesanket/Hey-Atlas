import asyncio
import numpy as np
from faster_whisper import WhisperModel


class SpeechToText:
    def __init__(self):
        self.sample_rate = 16000

        # Load model once
        self.model = WhisperModel(
            "base",
            device="cpu",
            compute_type="int8"
        )

    async def transcribe(self, pcm16_bytes: bytes) -> str:
        """
        Transcribe buffered PCM16 audio

        pcm16_bytes:
          - raw PCM16
          - mono
          - 16kHz
          - >= ~1 second recommended
        """

        if not pcm16_bytes or len(pcm16_bytes) < self.sample_rate * 2:
            # Too short to transcribe
            return ""

        # PCM16 → float32 numpy array
        audio = (
            np.frombuffer(pcm16_bytes, dtype=np.int16)
              .astype(np.float32) / 32768.0
        )   

        loop = asyncio.get_event_loop()
        segments, _ = await loop.run_in_executor(
            None,
            lambda: self.model.transcribe(audio, language="en")
        )

        text = "".join(segment.text for segment in segments).strip()
        return text
