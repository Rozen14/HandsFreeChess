import chess
import chess.engine
from pathlib import Path
import sys
import threading
import time

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from chess_rules.game_interface import GameState 
from voice_input.speech_to_text import SpeechRecognizer 
from voice_output.text_to_speech import TextToSpeech 
from app.board_view import SimpleBoardVisualizer as view
from controller import voice_game_controller as vgc
from app.app_loop import AppLoop
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
        Get Stockfish's move.
        """
        print("\n[Stockfish is thinking...]")     
        move = stockfish.get_move(game.board)
        uci_move = move.uci()
        print(f"[Stockfish plays: {uci_move}]")
        return uci_move
    
    controller.wait_for_opponent_move = wait_with_stockfish
    
    # Start speech recognition in background thread
    stt_thread = threading.Thread(
        target=recognizer.listen_loop,
        kwargs={"callback": controller.handle_speech},
        daemon=True
    )
    stt_thread.start()
    
    print("\n" + "=" * 60)
    print("Game started! You are WHITE, Stockfish is BLACK")
    print("Say your moves out loud (e.g., 'pawn to e4', 'knight f3')")
    print("Close the board window or press Ctrl+C to quit")
    print("=" * 60 + "\n")
    
    tts.speak("Game started. You are white. Make your move.")
    
    # Trigger initial render
    visualizer.render()
    
    # Start main application loop (handles pygame in main thread)
    app = AppLoop(controller, visualizer)
    
    try:
        app.run(tick_rate=60)
    except KeyboardInterrupt:
        print("\n\nGame interrupted by user")
    finally:
        app.stop()
        stockfish.close()
        recognizer.cleanup()
        tts.shutdown()
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
    visualizer.set_game(game)
    
    from voice_output.game_announcer import MoveAnnouncer
    announcer = MoveAnnouncer()
    
    move_count = 0
    last_move_time = time.time()
    move_delay = 1.0  # 1 second between moves
    
    print("\n" + "=" * 60)
    print("Watching Stockfish vs Stockfish")
    print("Close the board window to quit")
    print("=" * 60 + "\n")
    
    # Trigger initial render
    visualizer.render()
    
    try:
        while visualizer.running and not game.is_game_over() and move_count < 100:
            # Process pygame events
            if not visualizer.pump_events():
                break
            
            # Render board
            visualizer.render_if_needed()
            
            # Make move if enough time has passed 
            current_time = time.time()
            
            if current_time - last_move_time >= move_delay:
                # Determine whose turn
                is_white_turn = game.board.turn == chess.WHITE

                if is_white_turn:
                    # White's turn
                    print(f"\nMove {move_count + 1}: White")
                    move = white_engine.get_move(game.board)
                    color = "white"
                else:
                    # Black's turn
                    print(f"Move {move_count + 1}: Black")
                    move = black_engine.get_move(game.board)
                    color = "black"
                
                move_uci = move.uci()
                
                # Store board before move
                board_before = game.board.copy()
                
                # Apply move
                game.play_opponent_move(move_uci)
                
                # Announce
                move_desc = announcer.announce_move_from_board(move_uci, board_before)
                announcement = f"{color.capitalize()} {move_desc.lower()}"
                print(f"  {announcement}")
                tts.speak(announcement)

                # Trigger redraw
                visualizer.render()
            
                # Update timing
                last_move_time = current_time
                if is_white_turn:
                    move_count += 1
                    
                # Small delay for frame rate
                time.sleep(1/60)
                
            # Game over
            if game.is_game_over():
                result = game.get_result()
                print(f"\n{result}")
                tts.speak(f"Game over. {result}")
            
            print("\nPress Enter to exit...")
            input()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    finally:
        visualizer.stop()
        visualizer.close()
        white_engine.close()
        black_engine.close()
        tts.shutdown()
         
         
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