import numpy as np
from collections import deque

class VoiceActivityDetector:
    """
    Voice Activity Detection (VAD) - Detects when speech is present in audio
    Supports bi-directional / continuous conversation
    """
    
    def __init__(
        self,
        sample_rate=16000,
        frame_duration_ms=30,
        energy_threshold=0.03,
        speech_frames_threshold=2,
        silence_frames_threshold=20,
        pre_roll_frames=5
    ):
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.energy_threshold = energy_threshold
        self.speech_frames_threshold = speech_frames_threshold
        self.silence_frames_threshold = silence_frames_threshold
        
        # Frame size in samples
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)
        
        # Buffers and state
        self.audio_buffer = bytearray()
        self.speech_buffer = bytearray()       # Accumulate speech frames
        self.pre_speech_buffer = deque(maxlen=pre_roll_frames)  # Pre-roll frames
        self.energy_history = deque(maxlen=50)
        
        self.is_speaking = False
        self.speech_frames = 0
        self.silence_frames = 0
        
        print(f"✅ VAD initialized: threshold={energy_threshold}, frame_size={self.frame_size}")
    
    def calculate_energy(self, audio_data):
        """Calculate RMS energy of audio frame"""
        try:
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            if len(audio_array) == 0:
                return 0.0
            float_audio = audio_array.astype(np.float32) / 32768.0
            energy = np.sqrt(np.mean(float_audio ** 2))
            return energy
        except Exception as e:
            print(f"⚠️ Energy calculation error: {e}")
            return 0.0
    
    def _process_frame(self, frame):
        """Process a single frame and detect speech"""
        energy = self.calculate_energy(frame)
        self.energy_history.append(energy)
        
        # Adaptive threshold based on recent energies
        if len(self.energy_history) > 10:
            noise_floor = np.median(self.energy_history)
            threshold = max(self.energy_threshold, noise_floor * 1.5)
        else:
            threshold = self.energy_threshold
        
        # Always store frame in pre-roll
        self.pre_speech_buffer.append(frame)
        
        if energy > threshold:
            self.speech_frames += 1
            self.silence_frames = 0
            
            # Speech just started
            if not self.is_speaking and self.speech_frames >= self.speech_frames_threshold:
                self.is_speaking = True
                # Add pre-roll frames to speech buffer
                for f in self.pre_speech_buffer:
                    self.speech_buffer.extend(f)
                self.pre_speech_buffer.clear()
                print(f"🎤 Speech started (energy={energy:.4f})")
            
            # Add current frame to speech buffer if speaking
            if self.is_speaking:
                self.speech_buffer.extend(frame)
            
            return False, None
        
        else:
            # Silence frame
            self.silence_frames += 1
            if not self.is_speaking:
                self.speech_frames = 0  # reset if not speaking
            
            if self.is_speaking:
                self.speech_buffer.extend(frame)
            
            if self.is_speaking and self.silence_frames >= self.silence_frames_threshold:
                self.is_speaking = False
                print("🔇 Speech ended")
                speech_data = bytes(self.speech_buffer)
                self.speech_buffer.clear()
                self.speech_frames = 0
                self.pre_speech_buffer.clear()
                return True, speech_data
            
        return False, None
    
    def process_audio(self, audio_bytes):
        """Process incoming audio chunk (may contain multiple frames)"""
        self.audio_buffer.extend(audio_bytes)
        frame_bytes = self.frame_size * 2  # PCM16 = 2 bytes per sample
        speech_chunks = []
        
        while len(self.audio_buffer) >= frame_bytes:
            frame = bytes(self.audio_buffer[:frame_bytes])
            self.audio_buffer = self.audio_buffer[frame_bytes:]
            
            ended, speech_data = self._process_frame(frame)
            if ended and speech_data:
                speech_chunks.append(speech_data)
        
        # Return last speech chunk if any ended
        if speech_chunks:
            return True, speech_chunks[-1]
        return False, None
    
    def is_speech_ended(self):
        return not self.is_speaking and self.silence_frames >= self.silence_frames_threshold
    
    def clear_buffer(self):
        self.audio_buffer.clear()
        self.speech_buffer.clear()
        self.pre_speech_buffer.clear()
        self.speech_frames = 0
        self.silence_frames = 0
        self.is_speaking = False
        print("🧹 VAD buffer cleared")
    
    def get_stats(self):
        return {
            "is_speaking": self.is_speaking,
            "speech_frames": self.speech_frames,
            "silence_frames": self.silence_frames,
            "buffer_size": len(self.audio_buffer),
            "speech_buffer_size": len(self.speech_buffer),
            "recent_energy": list(self.energy_history)[-5:] if self.energy_history else []
        }
