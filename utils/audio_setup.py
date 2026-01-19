from voice_input import speech_to_text as stt
from voice_output.text_to_speech import TextToSpeech
from utils.audio_state import AudioStateManager
# TODO: Remove prints for proper logging


def setup_microphone():
    """Configure and return microphone index."""
    print("Available microphones:")
    stt.list_microphones()
    print()
    
    mic_index = int(input("Enter microphone index (or press Enter for default): ").strip())
    
    if mic_index:
        chosen_mic = stt.find_mic_by_index(mic_index)        
        
        if chosen_mic is not None:
            print(f"✓ Microphone found at index {mic_index}")
        else:
            print(f"⚠ Warning: No microphone found at index '{mic_index}'.")
            print("  Using system default microphone")
            mic_index = None  # Explicitly use system default
    else:
        # User pressed Enter - use system default
        print("Using system default microphone")
        mic_index = None
    
    return mic_index


def setup_audio_components(mic_index=None):
    """
    Initialize audio components with shared state manager.
    
    Args:
        mic_index: Microphone index (None for default)
        
    Returns:
        Tuple of (recognizer, tts, audio_state)
    """
    audio_state = AudioStateManager()
    
    recognizer = stt.SpeechRecognizer(
        mic_index=mic_index,
        phrase_time_limit=4,
        audio_state=audio_state
    )
    
    tts = TextToSpeech(audio_state=audio_state)
    
    return recognizer, tts, audio_state