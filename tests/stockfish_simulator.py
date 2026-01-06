import chess
import chess.engine
from pathlib import Path
import sys
import threading

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from chess_rules.game_interface import GameState 
from voice_input.speech_to_text import SpeechRecognizer 
from voice_output.text_to_speech import TextToSpeech 
from app.board_view import SimpleBoardVisualizer as view
from controller import voice_game_controller as vgc
import os


class StockfishOpponent:
    """
    Simulates an opponent using Stockfish engine.
    
    For testing purposes only, this will never connect to live games.
    """
    
    def __init__(self, stockfish_path: str, skill_level: int = 10, time_limit: float = 0.1):
        """
        Initialize Stockfish opponent.
        
        Args:
            stockfish_path: Path to Stockfish executable
            skill_level: Engine strength (0-20, where 0 is weakest)
            time_limit: Time in seconds for engine to think
        """
        self.engine = chess.engine.SimpleEngine.popen_uci(stockfish_path)
        self.skill_level = skill_level
        self.time_limit = time_limit
        
        # Configure engine strength
        self.engine.configure({"Skill Level": skill_level})
    
    def get_move(self, board: chess.Board) -> chess.Move:
        """
        Get Stockfish's move for the current position.
        
        Args:
            board: Current board state
            
        Returns:
            Move in chess.Move ()
        """
        result = self.engine.play(
            board,
            chess.engine.Limit(time=self.time_limit)
        )
        
        return result.move
    
    def close(self):
        """Clean up engine resources."""
        self.engine.quit()
        
def simulate_game_vs_stockfish():
    """
    Run a full game simulation against Stockfish.
    
    This lets you test the voice interface without needing to manually
    input opponent moves or connect to an online platform.
    """
    print("=" * 60)
    print("STOCKFISH TESTING MODE")
    print("=" * 60)
    print("\nThis mode lets you play against Stockfish to test the interface.")
    print("Your moves are voice-controlled, Stockfish responds automatically.\n")
    
    # Setup
    stockfish_path = input("Enter path to Stockfish executable (or press Enter for default): ").strip()
    if not stockfish_path:
        # Default to project assets folder
        project_root = Path(__file__).parent.parent
        if os.name == 'nt':  # Windows
            stockfish_path = project_root / "assets" / "stockfish" / "stockfish-windows-x86-64-avx2.exe"
        elif sys.platform == 'darwin':  # macOS
            stockfish_path = project_root / "assets" / "stockfish" / "stockfish-macos-m1-apple-silicon"
        else:  # Linux
            stockfish_path = project_root / "assets" / "stockfish" / "stockfish-ubuntu-x86-64-avx2"
        
        stockfish_path = str(stockfish_path)
    
    if not Path(stockfish_path).exists():
        print(f"Error: Stockfish not found at {stockfish_path}")
        print("Download from: https://stockfishchess.org/download/")
        print(f"Extract to: {Path(__file__).parent.parent / 'assets' / 'stockfish' / ''}")
        return
    
    skill = input("Stockfish skill level (0-20, default 10): ").strip()
    skill_level = int(skill) if skill else 10
    
    # Initialize components
    game = GameState(player_color="white")
    tts = TextToSpeech()
    
    # Setup microphone
    from voice_input import speech_to_text as stt
    print("\nAvailable microphones: ")    
    stt.list_microphones()
    print()
    
    mic_input = input("Enter microphone index (or press Enter for default): ").strip()
    mic_index = int(mic_input) if mic_input else None
    
    recognizer = SpeechRecognizer(mic_index=mic_index, phrase_time_limit=4)
    
    # Initialize Stockfish
    stockfish = StockfishOpponent(stockfish_path, skill_level=skill_level, time_limit=1.0)
    
    # Initialize visualizer
    visualizer = view()
    
    # Initialize controller (no simulation mode - Stockfish handles opponent)
    controller = vgc.GameController(game, tts, board_view=visualizer, opponent_type="stockfish")
    
    def wait_with_stockfish(timeout=360):
        """
        
        """
        print("\n[Stockfish is thinking...]")
        
        return stockfish.get_move(game.board)
    
    controller.wait_for_opponent_move = wait_with_stockfish
    
    print("\n" + "=" * 60)
    print("Game started! You are WHITE, Stockfish is BLACK")
    print("Say your moves out loud (e.g., 'pawn to e4', 'knight f3')")
    print("Close the board window or press Ctrl+C to quit")
    print("=" * 60 + "\n")
    
    tts.speak("Game started. You are white. Make your move.")
    
    # Render initial board
    visualizer.render()
    
    try:
        recognizer.listen_loop(callback=controller.handle_speech)
    except KeyboardInterrupt:
        print("\n\nGame interrupted by user")
    finally:
        stockfish.close()
        recognizer.cleanup()
        tts.shutdown()
        visualizer.close()
        print("\nGoodbye!")
    
def simulate_game_vs_itself():
    """
    Watch two Stockfish instances play against each other.
    
    Useful for testing announcements without voice input.
    """
    print("=" * 60)
    print("STOCKFISH VS STOCKFISH - AUTO-PLAY MODE")
    print("=" * 60)
    
    stockfish_path = input("Enter path to Stockfish: ").strip()
    
    if not Path(stockfish_path).exists():
        print(f"Error: Stockfish not found at {stockfish_path}")
        return
    
    # Two engines at different strengths
    white_engine = StockfishOpponent(stockfish_path, skill_level=5, time_limit=0.5)
    black_engine = StockfishOpponent(stockfish_path, skill_level=10, time_limit=0.5)
    
    game = GameState(player_color="white")
    tts = TextToSpeech()
    visualizer = view()
    
    from voice_output.game_announcer import MoveAnnouncer
    announcer = MoveAnnouncer()
    
    threading.Thread(
        target=visualizer.run,
        args=(game,),
        daemon=True
    ).start()
    
    move_count = 0
    
    try:
        while not game.is_game_over() and move_count < 100:
            # White's turn
            print(f"\nMove {move_count + 1}: White")
            move_san = white_engine.get_move(game.board)
            game.play_opponent_move(move_san)
            
            announcement = announcer.announce_opponent_move(move_san, "white")
            print(f"  {announcement}")
            tts.speak(announcement)
            
            visualizer.render()
            
            if game.is_game_over():
                break
            
            # Black's turn
            print(f"Move {move_count + 1}: Black")
            move_san = black_engine.get_move(game.board)
            game.play_opponent_move(move_san)
            
            announcement = announcer.announce_opponent_move(move_san, "black")
            print(f"  {announcement}")
            tts.speak(announcement)
            
            visualizer.render()
            
            move_count += 1
            
            import time
            time.sleep(0.5)  # Pause between moves
        # Game over
        result = game.get_result()
        print(f"\n{result}")
        tts.speak(f"Game over. {result}")
        
        input("\nPress Enter to exit...")
        
    finally:
        white_engine.close()
        black_engine.close()
        visualizer.close()
        
if __name__ == "__main__":
    print("Chess Testing Modes:\n")
    print("1. Play vs Stockfish (voice input)")
    print("2. Watch Stockfish vs Stockfish (auto-play)")
    print()
    
    choice = input("Choose mode (1 or 2): ").strip()
    
    if choice == "1":
        simulate_game_vs_stockfish()
    elif choice == "2":
        simulate_game_vs_itself()
    else:
        print("Invalid choice")
        
# python -m tests.stockfish_simulator