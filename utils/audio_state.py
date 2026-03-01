import threading
from enum import Enum
from typing import Optional, Callable
# TODO: Remove prints for proper logging

class AudioMode(Enum):
    """Current audio system state."""
    IDLE = "idle"           # Nothing happening
    SPEAKING = "speaking"   # TTS is active
    LISTENING = "listening" # STT is active
    
    
class AudioStateManager:
    """
    Coordinates STT and TTS to prevent them from interfering with each other.
    
    Ensures that:
    - STT doesn't listen while TTS is speaking
    - Proper sequencing of audio operations
    """
    
    def __init__(self):
        self._mode = AudioMode.IDLE
        self._lock = threading.RLock() # Reentrant lock for nested acquisitions
        self._mode_changed = threading.Condition(self._lock)
        
        # Callbacks for mode changes (optional, for debugging/logging)
        self._callbacks: list[Callable[[AudioMode, AudioMode], None]]  = []
    
    @property
    def mode(self) -> AudioMode:
        """Get current audio mode (thread-safe)."""
        with self._lock:
            return self._mode
        
    def is_speaking(self) -> bool:
        """Check if TTS is currently active."""
        return self.mode == AudioMode.SPEAKING
    
    def is_listening(self) -> bool:
        """Check if STT is currently active."""
        return self.mode == AudioMode.LISTENING
    
    def is_idle(self) -> bool:
        """Check if audio system is idle."""
        return self.mode == AudioMode.IDLE
    
    def set_mode(self, new_mode: AudioMode):
        """
        Set the audio mode and notify waiting threads.
        
        Args:
            new_mode: The mode to transition to
        """
        with self._lock:
            old_mode = self._mode
            if old_mode != new_mode:
                self._mode = new_mode
                self._mode_changed.notify_all()
                
                # Trigger callbacks
                for callback in self._callbacks:
                    try:
                        callback(old_mode, new_mode)                        
                    except Exception as e:
                        print(f"AudioState callback error: {e}")
    
    def wait_until_idle(self, timeout: Optional[float] = None) -> bool:
        """
        Block until audio system is idle.
        
        Args:
            timeout: Maximum seconds to wait (None = wait forever)
            
        Returns:
            True if idle, False if timeout occurred
        """
        with self._lock:
            if self._mode == AudioMode.IDLE:
                return True
            
            return self._mode_changed.wait_for(
                lambda: self._mode == AudioMode.IDLE,
                timeout=timeout
            )
            
    def wait_until_not_speaking(self, timeout: Optional[float] = None) -> bool:
        """
        Block until TTS finishes (mode is not SPEAKING).
        
        Useful for STT to wait before starting to listen.
        
        Args:
            timeout: Maximum seconds to wait (None = wait forever)
            
        Returns:
            True if not speaking, False if timeout occurred
        """
        with self._lock:
            if self._mode != AudioMode.SPEAKING:
                return True
            
            return self._mode_changed.wait_for(
                lambda: self._mode != AudioMode.SPEAKING,
                timeout=timeout
            )
            
    def register_callback(self, callback: Callable[[AudioMode, AudioMode], None]):
        """
        Register a callback for mode changes.
        
        Args:
            callback: Function(old_mode, new_mode) called on transitions
        """
        with self._lock:
            self._callbacks.append(callback)
            
    def unregister_callback(self, callback: Callable[[AudioMode, AudioMode], None]):
        """Unregister a previously registered callback."""
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)