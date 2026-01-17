import chess
import requests
from chess_rules import move_validator as mv
from chess_rules.move_parse_result import MoveParseResult, ParsedMove
# TODO: (Optional) add chess variants ie. chess960 etc.
# TODO: Refactor moves as to have relevant formatting...

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
        
        # Convert string to chess.Color internally
        self.player_color = chess.WHITE if player_color.lower() == "white" else chess.BLACK
    
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
    
    def parse_castling_intent(self, text: str) -> ParsedMove:
        """
        Parse user's castling command based on their color and perspective.
        
        Handles different ways users might express castling:
        - Absolute: "kingside", "queenside", "short", "long"
        - Directional: "left", "right" (depends on player color)
        - Generic: "castle" (checks which sides are legal)
        
        Args:
            text: User's voice command (e.g., "castle left")
            
        Returns:
            ParsedMove: (
                result: MoveParseResult(enum): 
                    {
                        OK = auto()
                        INVALID = auto()
                        NOT_UNDERSTOOD = auto()
                        AMBIGUOUS = auto()
                    }, 
                uci: str | None = None
            )
        """        
        # Check castling availability
        can_kingside = self.board.has_kingside_castling_rights(self.player_color)
        can_queenside = self.board.has_queenside_castling_rights(self.player_color)
        
        # No castling available
        if not can_kingside and not can_queenside:
            return ParsedMove(MoveParseResult.INVALID)
        
        text_lower = text.lower()
        
        # Determine which side is being requested (None if ambiguous/unclear)
        requested_side = self._parse_castle_side(text_lower)
        
        # Handle different outcomes
        if requested_side is None:
            # Could be ambiguous generic "castle" or not understood
            if "castle" in text_lower or "castles" in text_lower:
                if can_kingside and can_queenside:
                    return ParsedMove(MoveParseResult.AMBIGUOUS)
                # Only one option available - use it
                is_kingside = can_kingside  # True if kingside available, else False (queenside)
                return ParsedMove(MoveParseResult.OK, self._build_castle_uci(is_kingside))
            return ParsedMove(MoveParseResult.NOT_UNDERSTOOD)
        
        # Check if requested side is legal
        is_kingside = requested_side
        if (is_kingside and can_kingside) or (not is_kingside and can_queenside):
            return ParsedMove(MoveParseResult.OK, self._build_castle_uci(is_kingside))
        
        return ParsedMove(MoveParseResult.INVALID)    
    
    def _parse_castle_side(self, text_lower: str) -> bool:
        """
        Determine which castling side is requested from text.
        
        Args:
            text_lower: Lowercased user input
            
        Returns:
            True for kingside, False for queenside, None if ambiguous/unclear
        """
        # Absolute indicators
        if any(phrase in text_lower for phrase in ["queenside", "long", "o-o-o"]):
            return False
        
        if any(phrase in text_lower for phrase in ["kingside", "short", "o-o"]):
            return True
        
        # Directional indicators (depend on player color)
        if "left" in text_lower:
            # White's left = queenside, Black's left = kingside
            return self.player_color == chess.BLACK
        
        if "right" in text_lower:
            # White's right = kingside, Black's right = queenside
            return self.player_color == chess.WHITE
        
        # Ambiguous/unclear
        return None
    
    def _build_castle_uci(self, is_kingside: bool) -> str:
        """
        Build UCI notation for castling move.
        
        Args:
            is_kingside: True for kingside (O-O), False for queenside (O-O-O)
            
        Returns:
            UCI string (e.g., "e1g1" for white kingside)
        """
        rank = "1" if self.player_color == chess.WHITE else "8"
        # TODO: (Optional) Refactor target file and 'e' when implementing chess960
        target_file = "g" if is_kingside else "c"
        return f"e{rank}{target_file}{rank}"
    
    def play_move(self, move_uci: str) -> tuple[bool, str]:
        """
        Validate and execute a chess move in UCI notation.
        
        Args:
            move: Move in UCI notation (e.g., "e2e4")
            
        Returns:
            Tuple of (success, status):
            - (True, "move_executed") if move was successful            
            - (False, "illegal") if move is not legal
            - (False, "execution_failed") if move validation passed but execution failed
        """
        is_valid, error = self.validator.validate_move(move_uci)
        
        if not is_valid:
            return (False, error)                
        
        if self.validator.execute_move(move_uci):
            # TODO: Implement logic for actually making move on-site...
            return (True, "move_executed")
        
        return (False, "execution_failed")
    
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
    
    def play_opponent_move(self, move_uci: str) -> bool:
        """
        Execute opponent's move in UCI notation.
        
        Args:
            move: Corresponding move in UCI notation (e.g., "e7e5")
            
        Returns:
            True if successful, False otherwise
        """
        return self.validator.execute_move(move_uci)
            
    def fetch_current_state(self) -> str:
        # TODO: Implement platform-specific API calls.
        # Stub - in production this would call Chess.com/Lichess API
        return self.get_fen()
    
    def get_opponent_color_str(self) -> str:
        """
        Get opponent's color as a string.
        """
        return "black" if self.player_color == chess.WHITE else "white"
    
    def get_player_color_str(self) -> str:
        """
        Get player's color as a string.
        """
        return "white" if self.player_color == chess.WHITE else "black"
    
    def _build_castle(self, rank: str, dir: bool) -> str:
        """
        
        """
        # TODO: Finish implementation
        
        return 
    
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
        
            

