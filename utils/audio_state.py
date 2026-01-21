import threading
from enum import Enum
from typing import Optional, Callable
import time
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
                
                
class SpeakingContext:
    """
    Context manager for TTS operations.
    
    Usage:
        with SpeakingContext(audio_state):
            # TTS code here
            # Mode is automatically set to SPEAKING
        # Mode is automatically reset to IDLE when exiting
    """
    def __init__(self, audio_state: AudioStateManager, wait_for_idle: bool = True):
        """
        Args:
            audio_state: The shared AudioStateManager
            wait_for_idle: If True, wait for system to be idle before speaking
        """
        self.audio_state = audio_state
        self.wait_for_idle = wait_for_idle

    def __enter__(self)    :
        if self.wait_for_idle:
            # Wait for any existing speech/listening to finish
            if not self.audio_state.wait_until_idle(timeout=5.0):
                print("Warning: audio not idle, skipping TTS")
        
        self.audio_state.set_mode(AudioMode.SPEAKING)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Clean up when exiting the context.
        
        Args:
            exc_type: Exception type if an exception occurred, None otherwise
            exc_val: Exception value if an exception occurred, None otherwise
            exc_tb: Exception traceback if an exception occurred, None otherwise
            
        Returns:
            False to propagate any exception that occurred
        """
        # Always reset to IDLE, even if an exception occurred
        self.audio_state.set_mode(AudioMode.IDLE)
        # Return False means: don't suppress exceptions
        # If we returned True, exceptions would be silently caught
        return False

        
class ListeningContext: 
    """
    Context manager for STT operations.
    
    Usage:
        with ListeningContext(audio_state):
            # STT code here
            # Mode is automatically set to LISTENING (after waiting for TTS)
        # Mode is automatically reset to IDLE when exiting
    """
    def __init__(self, audio_state: AudioStateManager, wait_for_speech: bool = True):
        """
        Args:
            audio_state: The shared AudioStateManager
            wait_for_speech: If True, wait for TTS to finish before listening
        """
        self.audio_state = audio_state
        self.wait_for_speech = wait_for_speech

    def __enter__(self)    :
        if self.wait_for_speech:
            # Always wait for TTS to finish before listening
            if not self.audio_state.wait_until_not_speaking(timeout=10.0):
                print("Warning: Timeout waiting for TTS to finish")
        
        self.audio_state.set_mode(AudioMode.LISTENING)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Clean up when exiting the context.
        
        Args:
            exc_type: Exception type if an exception occurred, None otherwise
            exc_val: Exception value if an exception occurred, None otherwise
            exc_tb: Exception traceback if an exception occurred, None otherwise
            
        Returns:
            False to propagate any exception that occurred
        """        
        # Always reset to IDLE, even if an exception occurred
        self.audio_state.set_mode(AudioMode.IDLE)
        
        # Return False means: don't suppress exceptions
        return False
