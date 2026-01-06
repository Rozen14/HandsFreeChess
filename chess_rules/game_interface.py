import chess
import requests
from chess_rules import move_validator as mv
# TODO: (Optional) add chess variants ie. chess960 etc.

class GameState:
    """
    Manages the state of a chess game.
    
    Maintains the board position, handles move validation and execution,
    and provides utilities for querying game state (material count, game over, etc.).
    """
    
    def __init__(self, variant: str = "standard", player_color: str = "white") -> None:
        """
        Initialize a new game state.
        
        Args:
            variant: Chess variant ("standard" or "chess960")
            player_color: The color the user is playing (WHITE or BLACK)
        """
        self.board = chess.Board()
        self.validator = mv.MoveValidator(self.board)
        self.player_color = player_color
    
    def update_from_fen(self, fen: str) -> None:
        """
        Update the board state from a FEN string.
        
        Used when syncing with external game sources (Chess.com, Lichess).
        
        Args:
            fen: Forsyth-Edwards Notation string representing board position
        """
        self.board.set_fen(fen)
        # Update validator's board reference
        self.validator.board = self.board
    
    def parse_castling_intent(self, text: str) -> str | None:
        """
        Parse user's castling command based on their color and perspective.
        
        Handles different ways users might express castling:
        - Absolute: "kingside", "queenside", "short", "long"
        - Directional: "left", "right" (depends on player color)
        - Generic: "castle" (checks which sides are legal)
        
        Args:
            text: User's voice command (e.g., "castle left")
            
        Returns:
            - "O-O" for kingside castling
            - "O-O-O" for queenside castling  
            - "ambiguous" if both sides available
            - None if castling is not legal
        """        
        # Check what castling is available for current player
        if self.player_color == chess.WHITE:
            can_kingside = self.board.has_kingside_castling_rights(chess.WHITE)
            can_queenside = self.board.has_queenside_castling_rights(chess.WHITE)
        else:
            can_kingside = self.board.has_kingside_castling_rights(chess.BLACK)
            can_queenside = self.board.has_queenside_castling_rights(chess.BLACK)
            
        # No castling available at all
        if not can_kingside and not can_queenside:
            return None
        
        text_lower = text.lower()
        
        # These work regardless of color
        if any(phrase in text_lower for phrase in ["queenside", "long", "o-o-o", "0-0-0"]):
            return "O-O-O" if can_queenside else None
        
        if any(phrase in text_lower for phrase in ["kingside", "short", "o-o", "0-0"]):
            return "O-O" if can_kingside else None
        
        # Directional indicators
        if "left" in text_lower:
            # White's left = queenside, Black's left = kingside
            if self.player_color == chess.WHITE:
                return "O-O-O" if can_queenside else None
            else:
                return "O-O" if can_kingside else None
        
        if "right" in text_lower:
            #  White's right = kingside, Black's right = queenside
            if self.player_color == chess.WHITE:
                return "O-O" if can_kingside else None
            else:
                return "O-O-O" if can_queenside else None
            
        # Generic "castle" - check what's available
        if "castle" in text_lower or "castling" in text_lower:
            if can_kingside and can_queenside:
                return "ambiguous"
            elif can_kingside:
                return "O-O"
            elif can_queenside:
                return "O-O-O"
            
        return None
    
    def play_move(self, move: str) -> tuple[bool, str]:
        """
        Validate and execute a chess move.
        
        Args:
            move: Move in SAN or UCI notation (e.g., "Nf3", "e2e4", "O-O")
            
        Returns:
            Tuple of (success, status):
            - (True, "move_executed") if move was successful
            - (False, "ambiguous") if move needs clarification
            - (False, "illegal") if move is not legal
            - (False, "execution_failed") if move validation passed but execution failed
        """
        is_valid, error = self.validator.validate_move(move)
        
        if not is_valid:
            return (False, error)
        
        move_obj = self.validator.parse_move(move)
        
        if move_obj:
            self.board.push(move_obj)
            # TODO: Implement logic for actually making move on-site...
            return (True, "move_executed")
        
        return (False, "execution_failed")
    
    def handle_ambiguous_move(self, move: str, from_square: str) -> tuple[bool, str]:
        """
        Resolve and execute an ambiguous move.
        
        Takes an ambiguous move like "Re1" and a clarifying square like "a1",
        resolves it to "Rae1", then executes it.
        
        Args:
            move: Original ambiguous move (e.g., "Re1")
            from_square: Source square from user's clarification (e.g., "a1")
            
        Returns:
            Tuple of (success, status):
            - (True, "move_executed") if successful
            - (False, "invalid_square") if square doesn't match any legal move
            - (False, other) if execution failed for other reasons
        """
        resolved_move = self.validator.resolve_ambiguous_move(move, from_square)
        
        if resolved_move:
            return self.play_move(resolved_move)
        
        return (False, "invalid_square")
    
    def get_disambiguation_prompt(self, move: str) -> str:        
        """
        Get a clarification prompt for an ambiguous move.
        
        Args:
            move: Ambiguous move string (e.g., "Re1")
            
        Returns:
            Natural language prompt (e.g., "Which rook: a1 or h1?")
        """
        return self.validator.get_clarification_prompt(move)
    
    def material_balance(self) -> int:
        """
        Calculate material balance from white's perspective.
        
        Uses standard piece values: pawn=1, knight=3, bishop=3, rook=5, queen=9.
        Kings are not counted.
        
        Returns:
            Positive if white is ahead, negative if black is ahead, 0 if equal
        """
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
        """
        Get current board position in FEN notation.
        
        Returns:
            FEN string representing the current position
        """
        return self.board.fen()

    def is_game_over(self) -> bool:
        """
        Check if the game has ended.
        
        Returns:
            True if game is over (checkmate, stalemate, or draw), False otherwise
        """
        return self.board.is_game_over()
    
    def get_result(self) -> str:
        """
        Get the game result in human-readable format.
        
        Returns:
            "White wins", "Black wins", "Draw", or "Game in progress"
        """
        if not self.board.is_game_over():
            return "Game in progress"
        
        result = self.board.result()
        if result == "1-0":
            return "White wins"
        elif result == "0-1":
            return "Black wins"
        else:
            return "Draw"
    
    def material_summary(self):
        """
        Get detailed material count for both sides.
        
        Returns:
            Dictionary with structure:
            {
                "white": {"pawns": 8, "knights": 2, ...},
                "black": {"pawns": 8, "knights": 2, ...},
                "balance": -2  # positive = white ahead, negative = black ahead
            }
        """
        def count(color):
            return {
                "pawns": len(self.board.pieces(chess.PAWN, color)),
                "knights": len(self.board.pieces(chess.KNIGHT, color)),
                "bishops": len(self.board.pieces(chess.BISHOP, color)),
                "rooks": len(self.board.pieces(chess.ROOK, color)),
                "queens": len(self.board.pieces(chess.QUEEN, color))
            }
            
            
        return {
            "white": count(chess.WHITE),
            "black": count(chess.BLACK),
            "balance": self.material_balance()  
        }
        
    def get_last_move_san(self) -> str | None:
        """"""
        if self.board.move_stack:
            last_move = self.board.peek()
            # Temporarily pop to get proper SAN
            temp_move = self.board.pop()
            san = self.board.san(temp_move)
            self.board.push(temp_move)
            return san
        return None
    
    def play_opponent_move(self, move: str) -> None:
        """
        
        """
        # SAN
        try:
            move_obj = self.board.parse_san(move)
            self.board.push(move_obj)
            return True
        except:
            pass
        
        # UCI
        try: 
            move_obj = self.board.parse_uci(move)
            self.board.push(move_obj)
            return True
        except:
            pass
        
        # chess.Move
        try:
            self.board.push(move)
            return True
        except:
            return False
            
    def fetch_current_state(self) -> str:
        # TODO: Implement platform-specific API calls.
        # Stub - in production this would call Chess.com/Lichess API
        return self.get_fen()
        
# ---------------------------------------------------------
# CHESS.COM ADAPTER (stub until API access is granted)
# ---------------------------------------------------------
 
class ChessDotCom(GameState):
    """
    Chess.com game state adapter.
    
    Extends GameState to integrate with Chess.com's API.
    Currently a stub pending API access approval.
    """
    
    def __init__(self, board_region, variant: str = "standard", player_color: str = "white") -> None:
        """
        Initialize Chess.com game state.
        
        Args:
            board_region: Chess.com board region/server
            player_color: The color the user is playing
            variant: Chess variant
        """
        super().__init__(variant=variant, player_color=player_color)
        self.region = board_region
    
    def update_from_api(self, game_data: dict) -> None:
        """
        Update game state from Chess.com API response.
        
        Args:
            game_data: Dictionary containing game data from Chess.com API
        """
        if "fen" in game_data:
            self.update_from_fen(game_data["fen"])


# ---------------------------------------------------------
# LICHESS ADAPTER
# ---------------------------------------------------------

class LiChess(GameState):
    """
    Lichess game state adapter.
    
    Extends GameState to integrate with Lichess's API using token-based auth.
    """
    
    def __init__(self, token, variant: str = "standard", player_color: str = "white") -> None:
        """
        Initialize Lichess game state.
        
        Args:
            token: Lichess API authentication token
            player_color: The color the user is playing
            variant: Chess variant
        """
        super().__init__(variant=variant, player_color=player_color)
        self.headers = {
            "Authorization": f"Bearer {token}"
        }
    
    def fetch_game_state(self, game_id):
        """
        Fetch current game state from Lichess API.
        
        Streams game events and extracts the current FEN position.
        
        Args:
            game_id: Lichess game ID
            
        Returns:
            FEN string of current position, or None if unavailable
        """
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
        
            

