import chess
from typing import Optional, Tuple
from chess_rules.chess_enums.move_parse_result import MoveParseResult, ParsedMove
# TODO: (Optional) add chess 960 and variants

class MoveValidator:
    """
    Validates and executes chess moves using UCI notation.
    
    UCI (Universal Chess Interface) notation uses only coordinates (e.g., "e2e4", "e7e8q").
    This is simpler than SAN and doesn't have ambiguity issues.
    
    SINGLE SOURCE OF TRUTH for all move validation in the system.
    """
    
    def __init__(self, board: chess.Board):
        """
        Initialize the move validator.
        
        Args:
            board: The chess.Board instance to validate moves against
        """
        self.board = board    

    def parse_and_validate(self, move_uci: str) -> ParsedMove:
        """
        Parse UCI string and validate it as a legal move.
        
        This is the PRIMARY method - use this instead of separate parse/validate calls.
        
        Args:
            move_uci: Move in UCI notation (e.g., "e2e4", "e7e8q")
            
        Returns:
            ParsedMove with result and optional uci string
        """
        try: 
            move = chess.Move.from_uci(move_uci)
            if move in self.board.legal_moves:
                return ParsedMove(MoveParseResult.OK, move_uci)
            else:
                return ParsedMove(MoveParseResult.INVALID)
        except (ValueError, AssertionError):    
            return ParsedMove(MoveParseResult.INVALID)
    
    def is_legal(self, move_uci: str) -> bool:
        """
        Check if a UCI move string is legal.
        
        Args:
            move_str: Move in UCI notation (e.g. "e2e4", "e7e8q")
            
        Returns:
            True if the move is legal, False otherwise
        """
        result = self.parse_and_validate(move_uci)
        return result.result == MoveParseResult.OK
    
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
        result = self.parse_and_validate(move_str)
        if result.result == MoveParseResult.OK:
            return (True, None)
        else:
            return (False, "illegal")
    
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
        except (ValueError, AssertionError):
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