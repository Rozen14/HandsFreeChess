"""
Stockfish vs Stockfish auto-play mode.
Watch two engines play each other to test announcements without voice input.

Run with: python -m tests.stockfish_simulator
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import chess
from chess_rules.game_interface import GameState
from voice_output.text_to_speech import TextToSpeech
from voice_output.game_announcer import MoveAnnouncer
from app.board_view import SimpleBoardVisualizer
from utils.audio_state import AudioStateManager
from tests.test_modes import StockfishOpponent, get_stockfish_path

def main():
    """
    Watch two Stockfish instances play against each other.
    Useful for testing announcements without voice input.
    """
    print("=" * 60)
    print("STOCKFISH VS STOCKFISH - AUTO-PLAY MODE")
    print("=" * 60)
    
    try:
        stockfish_input = input("Enter path to Stockfish (or press Enter for default): ").strip()
        stockfish_path = get_stockfish_path(stockfish_input if stockfish_input else None)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return
    
    # Two engines at different strengths
    white_engine = StockfishOpponent(str(stockfish_path), skill_level=5, time_limit=0.5)
    black_engine = StockfishOpponent(str(stockfish_path), skill_level=10, time_limit=0.5)
    
    # Setup audio
    audio_state = AudioStateManager()
    tts = TextToSpeech(audio_state=audio_state)
    
    # Setup game
    game = GameState(player_color="white")
    visualizer = SimpleBoardVisualizer()
    visualizer.set_game(game)
    announcer = MoveAnnouncer()
    
    move_count = 0
    last_move_time = time.time()
    move_delay = 1.0  # 1 second between moves
    
    print("\n" + "=" * 60)
    print("Watching Stockfish vs Stockfish")
    print("Close the board window to quit")
    print("=" * 60 + "\n")
    
    visualizer.render()
    
    try:
        while visualizer.running and not game.is_game_over() and move_count < 100:
            if not visualizer.pump_events():
                break
            
            visualizer.render_if_needed()
            
            current_time = time.time()
            
            if current_time - last_move_time >= move_delay:
                is_white_turn = game.board.turn == chess.WHITE
                
                if is_white_turn:
                    print(f"\nMove {move_count + 1}: White")
                    move = white_engine.get_move(game.board)
                    color = "white"
                else:
                    print(f"Move {move_count + 1}: Black")
                    move = black_engine.get_move(game.board)
                    color = "black"
                
                move_uci = move.uci()
                board_before = game.board.copy()
                
                game.play_opponent_move(move_uci)
                
                move_desc = announcer.announce_move_from_board(move_uci, board_before)
                announcement = f"{color.capitalize()} {move_desc.lower()}"
                print(f"  {announcement}")
                tts.speak(announcement)
                
                visualizer.render()
                last_move_time = current_time
                
                if is_white_turn:
                    move_count += 1
                
                time.sleep(1/60)
            
            if game.is_game_over():
                result = game.get_result()
                print(f"\n{result}")
                tts.speak(f"Game over. {result}")
                break
                
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    finally:
        visualizer.stop()
        visualizer.close()
        white_engine.close()
        black_engine.close()
        tts.shutdown()
        print("\nGoodbye!")


if __name__ == "__main__":
    main()
