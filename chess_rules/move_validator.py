import chess
from typing import Optional, List, Tuple
# TODO: Add clarifications/comments etc.

class MoveClarifier:
    def __init__(self, board: chess.Board):
        self.board = board
    
    def is_ambiguous(self, move_str: str) -> bool:
        """Check if move is ambiguous (e.g., 'Re1' when both rooks can move there)"""
        try:
            # Try parsing - if it fails due to ambiguity, return True
            self.board.parse_san(move_str)
            return False
        except chess.AmbiguousMoveError:
            return True
        except (chess.InvalidMoveError, chess.IllegalMoveError):
            return False # Invalid, but not ambiguous
    
    def get_disambiguation_options(self, move_str: str) -> str:
        """Return list of possible moves (e.g., ['Rae1', 'Rhe1'])"""
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
        
        options = self.get_disambiguation_options(move_str)
        
        for san, from_sq in options:
            if from_sq == from_square.lower():
                return san
        
        return None

    def is_legal(self, move_str: str) -> bool:
        
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
        
        if self.is_ambiguous(move_str):
            return (False, "ambiguous")
        
        if not self.is_legal(move_str):
            return (False, "illegal")
        
        return (True, None)
    
    def execute_move(self, move_str: str) -> bool:
        
        # try UCI first
        try:
            uci_move = chess.Move.from_uci(move_str)
            if uci_move in self.board.legal_moves:
                self.board.push(uci_move)
                return True
        except:
            pass
        
        # fallback to SAN
        try:
            san_move = self.board.parse_san(move_str)
            self.board.push(san_move)
            return True
        except:
            return False
        