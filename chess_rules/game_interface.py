import chess
import requests
from chess_rules import move_validator as mv

class GameState:
    def __init__(self) -> None:
        self.board = chess.Board()
        self.validator = mv(self.board)
    
    def update_from_fen(self, fen: str) -> None:
        """Updates the internal board state."""
        self.board.set_fen(fen)
        # Update validator's board reference
        self.validator.board = self.board
    
    # TODO: reduce return types to max 2...
    def parse_castling_intent(self, text: str) -> str | None | tuple[str, list[str]]:
        
        text_lower = text.lower()
        
        # These work regardless of color
        if any(phrase in text_lower for phrase in ["queenside", "long", "o-o-o", "0-0-0"]):
            return "O-O-O"
        
        if any(phrase in text_lower for phrase in ["kingside", "short", "o-o", "0-0"]):
            return "O-O"
        
        # Directional indicators
        if "left" in text_lower:
            # From white's perspective: left = queenside
            # From black's perspective: left = kingside
            if self.player_color == chess.WHITE:
                return "O-O-O"  # Queenside
            else:
                return "O-O"    # Kingside
        
        if "right" in text_lower:
            # From white's perspective: right = kingside
            # From black's perspective: right = queenside
            if self.player_color == chess.WHITE:
                return "O-O"    # Kingside
            else:
                return "O-O-O"  # Queenside
            
        # Generic "castle" - check what's available
        if "castle" in text_lower or "castling" in text_lower:
            kingside_legal = self.validator.is_legal("O-O")
            queenside_legal = self.validator.is_legal("O-O-O")
            
            if kingside_legal and queenside_legal:
                # Both available - need clarification
                return ("ambiguous", ["O-O", "O-O-O"])
            elif kingside_legal:
                return "O-O"
            elif queenside_legal:
                return "O-O-O"
            else:
                # No castling available
                return None
            
        return None
    
    def play_move(self, move: str) -> tuple[bool, str]:
        """Apply a SAN or UCI move (e.g., 'Nf3' or 'g1f3')."""
        is_valid, error = self.validator.validate_move(move)
        
        if not is_valid:
            return (False, error)
        
        succes = self.validator.execute_move(move)
        
        if succes:
            # TODO: Add logic for actually making the move on site...
            return (True, "move_executed")
        
        return (False, "execution_failed")
    
    def handle_ambiguous_move(self, move: str, from_square: str) -> tuple[bool, str]:
        
        resolved_move = self.validator.resolve_ambiguous_move(move, from_square)
        
        if resolved_move:
            return self.play_move(resolved_move)
        
        return (False, "invalid_square")
    
    def get_disambiguation_prompt(self, move: str) -> str:
        
        return self.validator.get_clarification_prompt(move)
    
    def material_balance(self) -> int:
        """Returns material score for white minus black."""
        score = 0
        piece_values = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9,
        }

        for piece_type, value in piece_values.items():
            score += len(self.board.pieces(piece_type, chess.WHITE)) * value
            score -= len(self.board.pieces(piece_type, chess.BLACK)) * value

        return score
    
    def get_fen(self) -> str:
        return self.board.fen()

    def is_game_over(self) -> bool:
        return self.board.is_game_over()
    
    def get_result(self) -> str:
        if not self.board.is_game_over():
            return "Game in progress"
        
        result = self.board.result()
        if result == "1-0":
            return "White wins"
        elif result == "0-1":
            return "Black wins"
        else:
            return "Draw"
        
        
# ---------------------------------------------------------
# CHESS.COM ADAPTER (stub until API access is granted)
# ---------------------------------------------------------
 
class ChessDotCom(GameState):
    def __init__(self, board_region) -> None:
        super().__init__()
        self.region = board_region
    
    def update_from_api(self, game_data: dict) -> None:
        """
        Placeholder method. 
        """
        if "fen" in game_data:
            self.update_from_fen(game_data["fen"])


# ---------------------------------------------------------
# LICHESS ADAPTER
# ---------------------------------------------------------

class LiChess(GameState):
    def __init__(self, token) -> None:
        super().__init__()
        self.headers = {
            "Authorization": f"Bearer {token}"
        }
    
    def fetch_game_state(self, game_id):
        url = f"https://lichess.org/api/board/game/stream/{game_id}"
        response = requests.get(url, headers=self.headers, stream=True)

        for line in response.iter_lines():
            if line:
                event = line.decode("utf-8")
                if '"fen"' in event:
                    fen = event.split('"fen":"')[1].split('"')[0]
                    self.update_from_fen(fen)
                    return fen

        return None
        
            

