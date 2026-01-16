from chess_rules import game_interface as gi
from voice_input import speech_to_text as stt
from voice_output.text_to_speech import TextToSpeech
from controller import voice_game_controller as vgc
from utils.environment import setup_ffmpeg
from utils.audio_setup import setup_microphone 
from app.board_view import SimpleBoardVisualizer
import time
import threading

# TODO: Remove prints for proper logging...
# TODO: Migrate main to app/ when implementing minimal UI...


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
    tts = TextToSpeech()
    
    # Initialize game
    game = gi.GameState()
    # TODO: finish initialization of game...
    
    # Initialize visualizer
    board_view = SimpleBoardVisualizer()
    
    # Initialize controller
    controller = vgc.GameController(
        game, 
        tts, 
        board_view=board_view,
    
    ) 
    
    print("\nVoice Chess Interface Started")
    print("Say 'stop' to exit\n") # TODO: Implement exit
    
    # STT thread
    stt_thread = threading.Thread(
        target=recognizer.listen_loop,
        kwargs={"callback": controller.handle_speech},
        daemon = True
    )
    stt_thread.start()
    
    # Start APP LOOP
    # app = AppLoop(controller, board_view)
    
    try:
        # app.run()
        while True:
            time.sleep(0.1)
        
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        # app.stop()
        recognizer.cleanup()
        print("Goodbye!")

        
if __name__ == "__main__":
    main()