"""
Voice Chess Interface - Main Entry Point

Provides a simple menu for selecting game modes:
- Local game (manual opponent input for testing)
- Stockfish game (play against chess engine)
"""

from utils.game_modes import run_local_game, run_stockfish_game

# TODO: Remove prints for proper logging...
# TODO: Migrate main to app/ when implementing minimal UI...

def main():
    """Main application entry point with mode selection."""
    print("=" * 60)
    print("VOICE CHESS INTERFACE")
    print("=" * 60)
    print("\nSelect game mode:\n")
    print("1. Local game (manual opponent input)")
    print("2. Play vs Stockfish")
    print()
    
    choice = input("Choose mode (1 or 2): ").strip()
    
    if choice == "1":
        run_local_game()
    elif choice == "2":
        run_stockfish_game()
    else:
        print("Invalid choice. Exiting.")


if __name__ == "__main__":
    main()

