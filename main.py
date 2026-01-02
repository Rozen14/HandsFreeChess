from chess_rules import game_interface as gi
from voice_input import speech_to_text as stt
from voice_output.text_to_speech import TextToSpeech
from controller import voice_game_controller as vgc
import os
# TODO: Remove redundant tts.speak...
# TODO: Remove prints for proper logging...
# TODO: Migrate main to app/ when implementing minimal UI...
# TODO: Maybe move setup functions into utils/ (?)
# TODO: Check callback function...

def setup_ffmpeg():
    """Add ffmpeg to system PATH."""
    ffmpeg_path = r"C:\ffmpeg\ffmpeg-8.0.1-essentials_build\bin"
    os.environ["PATH"] += os.pathsep + ffmpeg_path


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


def setup_tts(rate=180, volume=1.0) -> TextToSpeech:
    return TextToSpeech(rate, volume)


def main():
    """Main application entry point."""
    setup_ffmpeg()
    mic_index = setup_microphone()
    
    # Initialize speech recognizer
    recognizer = stt.SpeechRecognizer(
        mic_index=mic_index,
        phrase_time_limit=4
    )
    
    # Initialize text to speech
    tts = setup_tts(rate=180, volume=1.0)
    
    # Initialize game
    game = gi.GameState()
    # TODO: finish initialization of game...
    # If user moves second, wait until opponent makes move, etc.
    # (keep in mind rematches etc.)
    
    # Initialize controller
    controller = vgc.GameController(game, tts)
    
    print("\nVoice Chess Interface Started")
    print("Say 'stop' to exit\n") # TODO: Implement exit
    
    try:
        # TODO: Add game and tts as passable inputs into function
        callback = controller.handle_speech
        
        recognizer.listen_loop(callback=callback)
        
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        recognizer.cleanup()
        print("Goodbye!")

        
if __name__ == "__main__":
    main()