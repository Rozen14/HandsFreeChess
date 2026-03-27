"""
Game mode runners for different types of chess games.
Handles initialization and execution of various game modes.
"""

import threading

from chess_rules import game_interface as gi
from controller import voice_game_controller as vgc
from app.board_view import SimpleBoardVisualizer
from app.app_loop import AppLoop
from utils.audio_setup import setup_microphone, setup_audio_components
from config import constants
from chess_rules.chess_enums.player_type import OpponentType as OT


# TODO: Remove prints for proper logging

def run_local_game():
    """
    Run a local game with manual opponent input (for testing).
    Opponent moves are entered via keyboard.
    """
    print("\n=== LOCAL GAME MODE ===")
    print("You'll manually enter opponent moves via keyboard.\n")

    mic_index = setup_microphone()
    recognizer, tts, cache, audio_state = setup_audio_components(mic_index)

    # Wait for cache to be ready
    cache.wait_for_cache_ready(timeout=30)

    game = gi.GameState(player_color="white")
    board_view = SimpleBoardVisualizer(audio_state=audio_state)

    controller = vgc.GameController(
        game,
        tts,
        board_view=board_view,
        opponent_type=OT.HUMAN
    )

    print("\nVoice Chess Interface Started")
    print("Opponent moves will be entered manually")
    print("Close the board window to exit\n")

    # STT thread
    stt_thread = threading.Thread(
        target=recognizer.listen_loop,
        kwargs={"callback": controller.handle_speech},
        daemon=True
    )
    stt_thread.start()

    # Start app loop
    app = AppLoop(controller, board_view)

    try:
        app.run()
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        app.stop()
        tts.shutdown()
        print("Goodbye!")


def run_stockfish_game():
    """
    Run a game against Stockfish engine.
    Uses voice input for player moves, Stockfish responds automatically.
    """
    print("\n=== STOCKFISH MODE ===")
    print("Play against the Stockfish engine.\n")
    
    # Import here to avoid dependency if not using this mode
    from tests.test_modes import StockfishOpponent, get_stockfish_path
    
    # Setup Stockfish
    try:
        stockfish_input = input("Enter path to Stockfish (or press Enter for default): ").strip()
        stockfish_path = get_stockfish_path(stockfish_input if stockfish_input else None)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return
    
    skill_input = input("Stockfish skill level (0-20, default 10): ").strip()
    skill_level = int(skill_input) if skill_input else constants.DEFAULT_SKILL_LEVEL
    
    # Setup audio
    mic_index = setup_microphone()
    recognizer, tts, cache, audio_state = setup_audio_components(mic_index)

    # Initialize game components
    game = gi.GameState(player_color="white")
    board_view = SimpleBoardVisualizer(audio_state=audio_state)
    stockfish = StockfishOpponent(str(stockfish_path), skill_level=skill_level, time_limit=constants.DEFAULT_THINK_TIME)

    controller = vgc.GameController(
        game,
        tts,
        board_view=board_view,
        opponent_type=OT.STOCKFISH
    )

    # Override wait_for_opponent_move to use Stockfish
    def wait_with_stockfish(timeout=constants.TIMEOUT_STOCKFISH):
        """Get Stockfish's move."""
        print("\n[Stockfish is thinking...]")
        move = stockfish.get_move(game.board)
        uci_move = move.uci()
        print(f"[Stockfish plays: {uci_move}]")
        return uci_move

    controller.wait_for_opponent_move = wait_with_stockfish

    # Start STT thread
    stt_thread = threading.Thread(
        target=recognizer.listen_loop,
        kwargs={"callback": controller.handle_speech},
        daemon=True
    )
    stt_thread.start()

    print("\n" + "=" * 60)
    print("Game started! You are WHITE, Stockfish is BLACK")
    print("Say your moves out loud (e.g., 'pawn to e4', 'knight f3')")
    print("Close the board window to quit")
    print("=" * 60 + "\n")

    tts.speak_tokens(["game started", "you are white", "make your move"], block=True)
    board_view.render()
    
    # Start app loop
    app = AppLoop(controller, board_view)
    
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
        

def run_online_game():
    # TODO: Implement
    pass