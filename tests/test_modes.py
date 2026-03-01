"""
Test modes for the chess interface.
Provides different opponent types and game modes for testing.
"""

import chess
import chess.engine
from pathlib import Path
from typing import Optional

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
            Move in chess.Move format
        """
        result = self.engine.play(
            board,
            chess.engine.Limit(time=self.time_limit)
        )
        
        return result.move
    
    def close(self):
        """Clean up engine resources."""
        self.engine.quit()

def get_stockfish_path(custom_path: Optional[str] = None) -> Path:
    """
    Get the Stockfish executable path.
    
    Args:
        custom_path: Optional custom path to Stockfish
        
    Returns:
        Path to Stockfish executable
        
    Raises:
        FileNotFoundError: If Stockfish is not found
    """
    if custom_path:
        path = Path(custom_path)
        if path.exists():
            return path
        raise FileNotFoundError(f"Stockfish not found at {custom_path}")
    
    # Default to project assets folder
    import sys
    import os
    
    project_root = Path(__file__).parent.parent
    
    if os.name == 'nt':  # Windows
        stockfish_path = project_root / "assets" / "stockfish" / "stockfish-windows-x86-64-avx2.exe"
    elif sys.platform == 'darwin':  # macOS
        stockfish_path = project_root / "assets" / "stockfish" / "stockfish-macos-m1-apple-silicon"
    else:  # Linux
        stockfish_path = project_root / "assets" / "stockfish" / "stockfish-ubuntu-x86-64-avx2"
    
    if not stockfish_path.exists():
        raise FileNotFoundError(
            f"Stockfish not found at {stockfish_path}\n"
            f"Download from: https://stockfishchess.org/download/\n"
            f"Extract to: {project_root / 'assets' / 'stockfish' / ''}"
        )
    
    return stockfish_path