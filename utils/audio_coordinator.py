from utils.audio_state import AudioStateManager
from voice_output.text_to_speech import TextToSpeech
from voice_input.speech_to_text import SpeechRecognizer

class AudioCoordinator:
    """Centralized audio management"""
    def __init__(self):
        self.state = AudioStateManager()
        self.tts = TextToSpeech(self.state)
        self.recognizer = SpeechRecognizer(self.state)
    
    def speak(self, text: str):
        self.tts.speak(text)
    
    def listen(self) -> str:
        return self.recognizer.listen_once()

# TODO: Implement inside necessary instances... 