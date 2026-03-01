from voice_input import speech_to_text as stt
from voice_output.atomic_cache import AtomicPhraseCache
from voice_output.streaming_tts import StreamingTTS
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
    audio_state = AudioStateManager()

    recognizer = stt.SpeechRecognizer(
        mic_index=mic_index,
        audio_state=audio_state,
    )

    cache = AtomicPhraseCache()
    cache.cache_vocabulary()

    tts = StreamingTTS(
        cache=cache,
        audio_state=audio_state,
    )

    return recognizer, tts, cache, audio_state