from enum import Enum
from collections import deque

class Turn(Enum):
    """Turn states"""
    USER = "user"
    ASSISTANT = "assistant"
    IDLE = "idle"

class TurnManager:
    """
    Manages conversation turns between user and assistant
    Prevents interruptions and ensures smooth turn-taking
    """
    
    def __init__(self):
        self.current_turn = Turn.USER
        self.user_audio_buffer = deque()
        self.turn_history = []
        print("✅ TurnManager initialized")
    
    def is_user_turn(self):
        """Check if it's the user's turn to speak"""
        return self.current_turn == Turn.USER or self.current_turn == Turn.IDLE
    
    def is_assistant_turn(self):
        """Check if it's the assistant's turn to speak"""
        return self.current_turn == Turn.ASSISTANT
    
    def set_user_turn(self):
        """Set turn to user"""
        self.current_turn = Turn.USER
        self._log_turn_change("User")
    
    def set_assistant_turn(self):
        """Set turn to assistant"""
        self.current_turn = Turn.ASSISTANT
        self._log_turn_change("Assistant")
    
    def set_idle(self):
        """Set turn to idle (no one speaking)"""
        self.current_turn = Turn.IDLE
        self._log_turn_change("Idle")
    
    def buffer_user_audio(self, audio_chunk):
        """
        Buffer user audio when assistant is speaking
        (For handling interruptions)
        """
        self.user_audio_buffer.append(audio_chunk)
        if len(self.user_audio_buffer) > 50:  # Limit buffer size
            self.user_audio_buffer.popleft()
    
    def get_buffered_audio(self):
        """Get and clear buffered user audio"""
        buffered = list(self.user_audio_buffer)
        self.user_audio_buffer.clear()
        return buffered
    
    def has_buffered_audio(self):
        """Check if there's buffered user audio"""
        return len(self.user_audio_buffer) > 0
    
    def reset(self):
        """Reset turn manager state"""
        self.current_turn = Turn.USER
        self.user_audio_buffer.clear()
        print("🔄 TurnManager reset")
    
    def _log_turn_change(self, turn_name):
        """Log turn changes for debugging"""
        self.turn_history.append({
            "turn": turn_name,
            "timestamp": self._get_timestamp()
        })
        print(f"🔄 Turn changed to: {turn_name}")
    
    def _get_timestamp(self):
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_state(self):
        """Get current state for debugging"""
        return {
            "current_turn": self.current_turn.value,
            "buffered_chunks": len(self.user_audio_buffer),
            "recent_turns": self.turn_history[-5:] if self.turn_history else []
        }