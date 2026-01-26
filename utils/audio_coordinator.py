from utils.audio_state import AudioStateManager
from voice_output.text_to_speech import TextToSpeech
from voice_input.speech_to_text import SpeechRecognizer
from typing import Optional

class AudioCoordinator:
    """
    Centralized audio management that ensures TTS and STT don't interfere.
    
    This is a convenience wrapper that manages the lifecycle of both
    audio components with shared state.
    """
    def __init__(self, mic_index: Optional[int] = None):
        """
        Initialize audio coordinator.
        
        Args:
            mic_index: Microphone index (None for default)
        """
        self.state = AudioStateManager()
        
        self.tts = TextToSpeech(self.state)
        
        self.recognizer = SpeechRecognizer(
            mic_index=mic_index,
            phrase_time_limit=4,
            audio_state=self.state
        )
    
    def speak(self, text: str):
        self.tts.speak(text)
    
    def listen(self) -> Optional[str]:
        return self.recognizer.listen_once()
    
    def listen_loop(self, callback):
        """Start continuous listening loop."""
        return self.recognizer.listen_loop(callback)
    
    def shutdown(self):
        """Clean up resources."""
        self.tts.shutdown()
        self.recognizer.cleanup()
    
    def get_cache_stats(self) -> dict:
        """Get TTS cache statistics."""
        return self.tts.get_cache_stats()
# TODO: Implement inside necessary instances... 