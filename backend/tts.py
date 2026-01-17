import asyncio
import numpy as np
import wave
import io

class TextToSpeech:
    """
    Text-to-Speech Module
    
    Implementation options:
    1. Coqui TTS (recommended - best quality)
    2. piper (fast, lightweight)
    3. gTTS (Google TTS, requires internet)
    """
    
    def __init__(self, engine="mock"):
        """
        Initialize TTS engine
        
        Args:
            engine: "coqui", "piper", "gtts", or "mock" (for testing)
        """
        self.engine = engine
        self.sample_rate = 16000
        
        if engine == "coqui":
            self._init_coqui()
        elif engine == "piper":
            self._init_piper()
        elif engine == "gtts":
            self._init_gtts()
        else:
            print("⚠️ Using MOCK TTS (for testing only)")
    
    def _init_coqui(self):
        """Initialize Coqui TTS"""
        try:
            from TTS.api import TTS
            
            print("🔄 Loading Coqui TTS model...")
            # Use a fast English model
            self.tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")
            print("✅ Coqui TTS loaded")
        except ImportError:
            print("❌ TTS not installed. Run: pip install TTS")
            self.engine = "mock"
        except Exception as e:
            print(f"❌ Error loading Coqui TTS: {e}")
            self.engine = "mock"
    
    def _init_piper(self):
        """Initialize piper TTS"""
        try:
            # piper-tts requires downloading voice models
            print("🔄 Loading piper TTS...")
            # You'll need to download a voice model
            # https://github.com/rhasspy/piper
            print("⚠️ Piper requires manual setup. Falling back to mock.")
            self.engine = "mock"
        except Exception as e:
            print(f"❌ Error loading piper: {e}")
            self.engine = "mock"
    
    def _init_gtts(self):
        """Initialize Google TTS"""
        try:
            from gtts import gTTS
            print("✅ gTTS ready (requires internet)")
        except ImportError:
            print("❌ gTTS not installed. Run: pip install gtts")
            self.engine = "mock"
    
    def wav_to_pcm16(self, wav_path):
        """Convert WAV file to PCM16 bytes"""
        try:
            with wave.open(wav_path, 'rb') as wav_file:
                # Read all frames
                frames = wav_file.readframes(wav_file.getnframes())
                
                # Get audio parameters
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                framerate = wav_file.getframerate()
                
                # Convert to numpy array
                audio_array = np.frombuffer(frames, dtype=np.int16)
                
                # Convert to mono if stereo
                if channels == 2:
                    audio_array = audio_array.reshape(-1, 2).mean(axis=1).astype(np.int16)
                
                # Resample if needed (simple method)
                if framerate != self.sample_rate:
                    # Basic resampling (for production, use scipy.signal.resample)
                    ratio = self.sample_rate / framerate
                    new_length = int(len(audio_array) * ratio)
                    audio_array = np.interp(
                        np.linspace(0, len(audio_array), new_length),
                        np.arange(len(audio_array)),
                        audio_array
                    ).astype(np.int16)
                
                return audio_array.tobytes()
        except Exception as e:
            print(f"❌ WAV conversion error: {e}")
            return b""
    
    async def synthesize(self, text):
        """
        Synthesize speech from text
        
        Args:
            text: Text to synthesize
            
        Returns:
            bytes: PCM16 audio data at 16kHz
        """
        if not text or len(text.strip()) == 0:
            return b""
        
        if self.engine == "coqui":
            return await self._synthesize_coqui(text)
        elif self.engine == "piper":
            return await self._synthesize_piper(text)
        elif self.engine == "gtts":
            return await self._synthesize_gtts(text)
        else:
            return await self._synthesize_mock(text)
    
    async def _synthesize_coqui(self, text):
        """Synthesize using Coqui TTS"""
        try:
            # Generate to temp file
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            # Run synthesis in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.tts.tts_to_file(text=text, file_path=tmp_path)
            )
            
            # Convert to PCM16
            pcm_data = self.wav_to_pcm16(tmp_path)
            
            # Clean up
            os.unlink(tmp_path)
            
            return pcm_data
            
        except Exception as e:
            print(f"❌ Coqui synthesis error: {e}")
            return b""
    
    async def _synthesize_piper(self, text):
        """Synthesize using piper"""
        # Placeholder for piper implementation
        return await self._synthesize_mock(text)
    
    async def _synthesize_gtts(self, text):
        """Synthesize using Google TTS"""
        try:
            from gtts import gTTS
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            # Generate speech
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: gTTS(text=text, lang='en', slow=False).save(tmp_path)
            )
            
            # Convert MP3 to WAV then to PCM16
            # Note: You'll need pydub and ffmpeg for this
            try:
                from pydub import AudioSegment
                
                audio = AudioSegment.from_mp3(tmp_path)
                
                # Export as WAV
                wav_path = tmp_path.replace(".mp3", ".wav")
                audio.export(wav_path, format="wav")
                
                # Convert to PCM16
                pcm_data = self.wav_to_pcm16(wav_path)
                
                # Clean up
                os.unlink(tmp_path)
                os.unlink(wav_path)
                
                return pcm_data
            except ImportError:
                print("❌ pydub not installed. Run: pip install pydub")
                os.unlink(tmp_path)
                return b""
            
        except Exception as e:
            print(f"❌ gTTS synthesis error: {e}")
            return b""
    
    async def _synthesize_mock(self, text):
        """Mock synthesis for testing - generates simple beep tone"""
        # Simulate processing delay
        await asyncio.sleep(0.3)
        
        # Generate a simple beep tone as placeholder
        # Duration based on text length (50ms per character, max 3 seconds)
        duration = min(len(text) * 0.05, 3.0)
        num_samples = int(self.sample_rate * duration)
        
        # Generate 440Hz sine wave (musical note A)
        t = np.linspace(0, duration, num_samples)
        frequency = 440  # Hz
        audio = np.sin(2 * np.pi * frequency * t)
        
        # Apply envelope to avoid clicks
        envelope = np.ones(num_samples)
        fade_samples = int(self.sample_rate * 0.05)  # 50ms fade
        envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
        envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)
        audio *= envelope
        
        # Convert to PCM16
        audio_pcm16 = (audio * 32767 * 0.3).astype(np.int16)  # 30% volume
        
        print(f"🔊 Generated {duration:.1f}s beep for: '{text[:50]}...'")
        return audio_pcm16.tobytes()


# Quick test
if __name__ == "__main__":
    import asyncio
    
    async def test():
        tts = TextToSpeech(engine="mock")
        
        audio = await tts.synthesize("Hello, this is a test.")
        print(f"Generated {len(audio)} bytes of audio")
        
        # Save to file for testing
        with wave.open("test_output.wav", 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(audio)
        print("Saved to test_output.wav")
    
    asyncio.run(test())