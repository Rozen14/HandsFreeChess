import chess
from typing import Optional, List, Tuple
# TODO: (Optional) add chess 960 and variants
# TODO: (V1.0) Refactor... Most of the logic can go through python-chess library...

class MoveValidator:
    """
    Validates, disambiguates, and executes chess moves.
    
    This class handles all move validation logic including checking for
    ambiguous moves, generating clarification prompts, and executing
    validated moves on the board.
    """
    
    def __init__(self, board: chess.Board):
        """
        Initialize the move validator.
        
        Args:
            board: The chess.Board instance to validate moves against
        """
        self.board = board
    
    def is_ambiguous(self, move_str: str) -> bool:
        """
        Check if a move string is ambiguous.
        
        A move is ambiguous when multiple pieces of the same type can move
        to the same square. For example, "Re1" when both rooks can move to e1.
        
        Args:
            move_str: Move in SAN notation (e.g., "Re1", "Nf3")
            
        Returns:
            True if the move is ambiguous, False otherwise
        """
        try:
            # Try parsing - if it fails due to ambiguity, return True
            self.board.parse_san(move_str)
            return False
        except chess.AmbiguousMoveError:
            return True
        except (chess.InvalidMoveError, chess.IllegalMoveError):
            return False # Invalid, but not ambiguous
    
    def get_disambiguation_options(self, move_str: str) -> str:
        """
        Get all legal moves that match an ambiguous move pattern.
        
        For an ambiguous move like "Re1", this returns all possible moves
        with their source squares, e.g., [("Rae1", "a1"), ("Rhe1", "h1")].
        
        Args:
            move_str: Ambiguous move string (e.g., "Re1")
            
        Returns:
            List of tuples containing (fully_qualified_san, from_square)
            Example: [("Rae1", "a1"), ("Rhe1", "h1")]
        """
        options = []
        
        # Extract destination square from move string
        # Handles captures
        dest = move_str.replace("x", "")[-2:]
        
        # Get piece type from move string
        piece_char = move_str[0] if move_str[0].isupper() else "P"
        piece_map = {'K': chess.KING, 'Q': chess.QUEEN, 'R': chess.ROOK, 
                     'B': chess.BISHOP, 'N': chess.KNIGHT, 'P': chess.PAWN}
        piece_type = piece_map.get(piece_char)
        
        if not piece_type:
            return options
        
        # Find all legal moves matching the pattern 
        for move in self.board.legal_moves:
            moving_piece = self.board.piece_at(move.from_square)
            
            # Check if this move matches our criteria
            if (moving_piece and 
                moving_piece.piece_type == piece_type and 
                chess.square_name(move.to_square) == dest):
                
                # Get fully qualified SAN for this move
                san = self.board.san(move)
                from_sq = chess.square_name(move.from_square)
                options.append((san, from_sq))
                
        return options
    
    def get_clarification_prompt(self, move_str: str) -> str:
        """
        Generate a natural language prompt asking for clarification.
        
        Creates a user-friendly prompt like "Which rook: a1 or h1?" for
        ambiguous moves.
        
        Args:
            move_str: Ambiguous move string (e.g., "Re1")
            
        Returns:
            Natural language clarification prompt
            Example: "Which rook: a1 or h1?"
        """
        options = self.get_disambiguation_options(move_str)
        
        if not options:
            return f"Could not find any legal moves matching '{move_str}'" 
        
        # Extract piece name
        piece_names = {'K': 'king', 'Q': 'queen', 'R': 'rook', 
                       'B': 'bishop', 'N': 'knight'}
        piece_name = piece_names.get(move_str[0], 'pawn')
        
        # Build prompt
        squares = [from_sq for _, from_sq in options]
        if len(squares) == 2: 
            return f"Which {piece_name}: {squares[0]} or {squares[1]}?"
        else:
            square_list = ", ".join(squares[:-1]) + f", or {squares[-1]}"
            return f"Which {piece_name}: {square_list}?"
    
    def resolve_ambiguous_move(self, move_str: str, from_square: str) -> Optional[str]:
        """
        Resolve an ambiguous move given the source square.
        
        Takes an ambiguous move like "Re1" and a clarifying square like "a1",
        then returns the fully qualified move "Rae1".
        
        Args:
            move_str: Original ambiguous move (e.g., "Re1")
            from_square: Source square chosen by user (e.g., "a1")
            
        Returns:
            Fully qualified SAN move string (e.g., "Rae1"), or None if invalid
        """
        options = self.get_disambiguation_options(move_str)
        
        for san, from_sq in options:
            if from_sq == from_square.lower():
                return san
        
        return None

    def is_legal(self, move_str: str) -> bool:
        """
        Check if a move string represents a legal move.
        
        Attempts to parse the move as both UCI and SAN notation to determine
        if it's legal in the current board position.
        
        Args:
            move_str: Move in SAN or UCI notation (e.g., "Nf3", "e2e4")
            
        Returns:
            True if the move is legal, False otherwise
        """
        # Try UCI first
        try:
            uci_move = chess.Move.from_uci(move_str)
            return uci_move in self.board.legal_moves
        except:
            pass
        
        # Try SAN
        try:
            san_move = self.board.parse_san(move_str)
            return san_move in self.board.legal_moves
        except:
            return False
    
    def validate_move(self, move_str: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a move and return its status.
        
        Checks if a move is legal and unambiguous before execution.
        
        Args:
            move_str: Move in SAN or UCI notation
            
        Returns:
            Tuple of (is_valid, error_type):
            - (True, None) if valid and ready to execute
            - (False, "ambiguous") if needs clarification
            - (False, "illegal") if move is not legal
        """
        if self.is_ambiguous(move_str):
            return (False, "ambiguous")
        
        if not self.is_legal(move_str):
            return (False, "illegal")
        
        return (True, None)
    
    def parse_move(self, move_str: str) -> chess.Move | None:
        """
        Parse a move string into a chess.Move object.
        
        Attempts to parse the move in both UCI and SAN formats, returning
        the Move object if valid. This method assumes the move has already
        been validated - it does not check legality beyond what's required
        for parsing.
        
        Args:
            move_str: Move in SAN or UCI notation (e.g., "Nf3", "e2e4", "O-O")
            
        Returns:
            chess.Move object if parsing succeeds, None if the move cannot
            be parsed or is not in the list of legal moves
            
        Note:
            This method should be called after validate_move() confirms the
            move is legal and unambiguous.
        """
        
        # try UCI first
        try:
            uci_move = chess.Move.from_uci(move_str)
            if uci_move in self.board.legal_moves:                
                return uci_move
        except:
            pass
        
        # fallback to SAN
        try:
            san_move = self.board.parse_san(move_str)
            return san_move
        except:
            return None
        