import asyncio
import numpy as np
import wave
import io
import os
import tempfile


class TextToSpeech:
    """
    Text-to-Speech Module

    Engines supported:
    - mock   : Robot-like speech (offline, fast, for POC)
    - coqui  : High-quality neural TTS
    - gtts   : Google TTS (internet required)
    """

    def __init__(self, engine="mock"):
        self.engine = engine
        self.sample_rate = 16000

        if engine == "coqui":
            self._init_coqui()
        elif engine == "gtts":
            self._init_gtts()
        else:
            print("⚠️ Using MOCK TTS (robot speech, offline)")

    # ------------------------------------------------------------------
    # Engine Initializers
    # ------------------------------------------------------------------

    def _init_coqui(self):
        try:
            from TTS.api import TTS
            print("🔄 Loading Coqui TTS model...")
            self.tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")
            print("✅ Coqui TTS loaded")
        except Exception as e:
            print(f"❌ Coqui init failed: {e}")
            self.engine = "mock"

    def _init_gtts(self):
        try:
            from gtts import gTTS
            print("✅ gTTS ready (internet required)")
        except Exception as e:
            print(f"❌ gTTS init failed: {e}")
            self.engine = "mock"

    # ------------------------------------------------------------------
    # WAV → PCM16 Converter
    # ------------------------------------------------------------------

    def wav_to_pcm16(self, wav_path):
        try:
            with wave.open(wav_path, "rb") as wav_file:
                frames = wav_file.readframes(wav_file.getnframes())
                channels = wav_file.getnchannels()
                rate = wav_file.getframerate()

                audio = np.frombuffer(frames, dtype=np.int16)

                if channels == 2:
                    audio = audio.reshape(-1, 2).mean(axis=1).astype(np.int16)

                if rate != self.sample_rate:
                    ratio = self.sample_rate / rate
                    new_len = int(len(audio) * ratio)
                    audio = np.interp(
                        np.linspace(0, len(audio), new_len),
                        np.arange(len(audio)),
                        audio,
                    ).astype(np.int16)

                return audio.tobytes()
        except Exception as e:
            print(f"❌ WAV conversion error: {e}")
            return b""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def synthesize(self, text: str) -> bytes:
        if not text or not text.strip():
            return b""

        if self.engine == "coqui":
            return await self._synthesize_coqui(text)
        elif self.engine == "gtts":
            return await self._synthesize_gtts(text)
        else:
            return await self._synthesize_mock(text)

    # ------------------------------------------------------------------
    # Coqui TTS
    # ------------------------------------------------------------------

    async def _synthesize_coqui(self, text):
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                path = f.name

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, lambda: self.tts.tts_to_file(text=text, file_path=path)
            )

            pcm = self.wav_to_pcm16(path)
            os.unlink(path)
            return pcm
        except Exception as e:
            print(f"❌ Coqui synthesis error: {e}")
            return b""

    # ------------------------------------------------------------------
    # gTTS
    # ------------------------------------------------------------------

    async def _synthesize_gtts(self, text):
        try:
            from gtts import gTTS
            from pydub import AudioSegment

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                mp3_path = f.name

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, lambda: gTTS(text=text, lang="en").save(mp3_path)
            )

            wav_path = mp3_path.replace(".mp3", ".wav")
            AudioSegment.from_mp3(mp3_path).export(wav_path, format="wav")

            pcm = self.wav_to_pcm16(wav_path)

            os.unlink(mp3_path)
            os.unlink(wav_path)
            return pcm
        except Exception as e:
            print(f"❌ gTTS synthesis error: {e}")
            return b""

    # ------------------------------------------------------------------
    # MOCK (ROBOT SPEECH – NOT BEEP)
    # ------------------------------------------------------------------

    async def _synthesize_mock(self, text):
        """
        ROBOT-LIKE speech mock (voiced + formants)
        Not real TTS, but sounds like talking
        """

        print(f"🗣️ MOCK SPEECH for: '{text[:40]}...'")
       
        await asyncio.sleep(0.03)

        sr = self.sample_rate
        duration = min(len(text) * 0.06, 5.0)
        n = int(sr * duration)
        t = np.linspace(0, duration, n, endpoint=False)

        # 1️⃣ Fundamental pitch (robot voice)
        f0 = np.random.uniform(90, 160)  # Hz
        voiced = np.sin(2 * np.pi * f0 * t)

        # 2️⃣ Add harmonics
        for h in range(2, 5):
            voiced += (1 / h) * np.sin(2 * np.pi * f0 * h * t)

        # 3️⃣ Fake vowel formants (band emphasis)
        formant_freqs = np.random.choice(
            [500, 700, 1100, 1500, 2300], size=2, replace=False
        )

        for f in formant_freqs:
            voiced += 0.3 * np.sin(2 * np.pi * f * t)

        # 4️⃣ Amplitude envelope (syllables)
        syllable_rate = np.random.uniform(3, 6)
        envelope = 0.5 * (1 + np.sin(2 * np.pi * syllable_rate * t))
        audio = voiced * envelope

        # 5️⃣ Normalize
        audio /= np.max(np.abs(audio) + 1e-6)

        pcm16 = (audio * 32767 * 0.5).astype(np.int16)
        return pcm16.tobytes()




# ------------------------------------------------------------------
# Quick Test
# ------------------------------------------------------------------

if __name__ == "__main__":

    async def test():
        tts = TextToSpeech(engine="mock")

        audio = await tts.synthesize("Hello Sanket, your voice system is working.")
        print(f"Generated {len(audio)} bytes")

        with wave.open("test_output.wav", "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            w.writeframes(audio)

        print("✅ Saved test_output.wav")

    asyncio.run(test())
