from chess_rules import game_interface as gi
from voice_input import intent_classifier as intent
from voice_input import move_parser as mp
from voice_input import speech_to_text as SpeechRecognizer
from voice_output.text_to_speech import TextToSpeech
import os

# Global game state and TTS
game = None
tts = None
recognizer = None
waiting_for_clarification = False
pending_move = None

def setup_ffmpeg():
    """Add ffmpeg to system PATH."""
    ffmpeg_path = r"C:\ffmpeg\ffmpeg-8.0.1-essentials_build\bin"
    os.environ["PATH"] += os.pathsep + ffmpeg_path


def setup_microphone():
    """Configure and return microphone index."""
    print("Available microphones:")
    SpeechRecognizer.list_microphones()
    print()
    
    chosen_mic = input("Enter microphone name (or press Enter for default): ").strip()
    
    if not chosen_mic:
        chosen_mic = "Micrófono externo (Realtek(R) Audio)"
        print(f"Using default: {chosen_mic}")
    
    mic_index = SpeechRecognizer.find_mic_index(chosen_mic)
    
    if mic_index is None:
        print(f"Warning: '{chosen_mic}' not found, using default microphone")
    else:
        print(f"⚠ Warning: '{chosen_mic}' not found")
        print("  Using system default microphone")
    
    return mic_index


def handle_clarification(text: str) -> bool:
    # TODO: check/define scope of function (if it will work only for ambiguity or also for illegal moves...)
    global waiting_for_clarification, pending_move
    
    # TODO: check implementation inside move_parser.py
    from_square = mp.extract_square(text) 
    
    if from_square:
        success, error = game.handle_ambiguous_move(pending_move, from_square)
        
        if success: 
            tts.speak(f"Moved {pending_move} from {from_square}")
            
            waiting_for_clarification = False 
            pending_move = None
            
            if game.is_game_over():
                result = game.get_result()
                tts.speak(f"Game over. {result}")
                return False
            
        else: 
            tts.speak("That square doesn't match any legal move. Please try again.")
            return True
    else:
        tts.speak("I didn't understand. Please say the square, like 'a1' or 'h8'.")
        return True
    
    return ...


def handle_speech(text: str):
    """Process recognized speech and execute chess commands."""
    intent_type = intent.predict(text)
    
    if intent_type == "move" or intent_type == "uci_move":
        parsed_move = mp.parse_move(text)
        
        if not parsed_move:
            tts.speak("Could not understand move. Please try again.")
            return True
        
        success, error = game.play_move(parsed_move)
        
        if success:
            # TODO: Execute move logic...
            tts.speak(f"Moved {parsed_move}")            
        elif error == "ambiguous":
            # Handle disambiguation
            prompt = game.get_disambiguation_prompt(parsed_move)
            tts.speak(prompt)
            # TODO: Listen for clarification, then call:
            # game.handle_ambiguous_move(parsed_move, from_square)
        else:
            tts.speak("Invalid move")
        
    # TODO: Handle other intents...
    # if intent_type == "":
    
    return True


def main():
    """Main application entry point."""
    setup_ffmpeg()
    mic_index = setup_microphone()
    
    # Initialize speech recognizer
    recognizer = SpeechRecognizer(
        mic_index=mic_index,
        phrase_time_limit=4
    )
    
    print("\nVoice Chess Interface Started")
    print("Say 'stop' to exit\n")
    
    try:
        recognizer.listen_loop(callback=handle_speech)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        recognizer.cleanup()
        print("Goodbye!")

        
if __name__ == "__main__":
    main()