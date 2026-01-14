import chess
from typing import Optional, Tuple
# TODO: (Optional) add chess 960 and variants

class MoveValidator:
    """
    Validates and executes chess moves using UCI notation.
    
    UCI (Universal Chess Interface) notation uses only coordinates (e.g., "e2e4", "e7e8q").
    This is simpler than SAN and doesn't have ambiguity issues.
    """
    
    def __init__(self, board: chess.Board):
        """
        Initialize the move validator.
        
        Args:
            board: The chess.Board instance to validate moves against
        """
        self.board = board    

    def is_legal(self, move_uci: str) -> bool:
        """
        Check if a UCI move string is legal.
        
        Args:
            move_str: Move in UCI notation (e.g. "e2e4", "e7e8q")
            
        Returns:
            True if the move is legal, False otherwise
        """
        return self.parse_move(move_uci) is not None
    
    def validate_move(self, move_str: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a UCI move.
        
        Args:
            move_uci: Move in UCI notation (e.g., "e2e4")
            
        Returns:
            Tuple of (is_valid, error_type):
            - (True, None) if valid and ready to execute
            - (False, "illegal") if move is not legal
        """        
        if not self.is_legal(move_str):
            return (False, "illegal")
        
        return (True, None)
    
    def parse_move(self, move_uci: str) -> chess.Move | None:
        """
        Parse a UCI move string into a chess.Move object.
        
        Args:
            move_uci: Move in UCI notation (e.g., "e2e4", "e7e8q")
            
        Returns:
            chess.Move object if valid, None otherwise
        """
        try:
            move = chess.Move.from_uci(move_uci)
            if move in self.board.legal_moves:
                return move
            return None
        except:
            return None            
        
    def execute_move(self, move_uci: str) -> bool:
        """
        Execute a validated UCI move on the board.
        
        Args:
            move_uci: Move in UCI notation
            
        Returns:
            True if successful, False otherwise
        """
        move = self.parse_move(move_uci)
        if move:
            self.board.push(move)
            return True
        return False