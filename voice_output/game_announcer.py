import re 
import chess 
from typing import Optional
from chess_rules.chess_enums.move_parse_result import MoveParseResult, ParsedMove
# TODO: Finish...
# TODO: Refactor to use UCI...
# TODO: Maybe add variation to phrases(?)

class MoveAnnouncer:
    """
    Converts chess moves and game data into natural language announcements.
    This class works as the bridge between what happens and what TTS says.
    
    This class works with strings and simple data types, not chess objects.
    All chess logic should remain in chess_rules/ modules.
    """
    
    def __init__(self):
        self.piece_symbols = {
            chess.KING: "king",
            chess.QUEEN: "queen",
            chess.ROOK: "rook",
            chess.BISHOP: "bishop",
            chess.KNIGHT: "knight",
            chess.PAWN: "pawn"
        }
    
    def announce_move_from_board(self, move_uci: str, board: chess.Board) -> str:
        """
        PRIMARY METHOD: Announce a move by inspecting the board state.
        
        This is the recommended method for all move announcements.
        
        Args:
            move_uci: Move in UCI notation
            board: Board state BEFORE the move
            
        Returns:
            Natural language description
        """
        try:
            move = chess.Move.from_uci(move_uci)
        except (ValueError, AssertionError):
            return "Invalid move"
        
        from_square = move.from_square
        to_square = move.to_square
        
        # Get the piece that's moving
        piece = board.piece_at(from_square)
        if not piece:
            return "Invalid move"
        
        piece_type = piece.piece_type
        piece_name = self.piece_symbols[piece_type]
        
        # Get destination square name
        dest = chess.square_name(to_square)
        
        # Check for castling
        if piece_type == chess.KING:
            from_file = chess.square_file(from_square)
            to_file = chess.square_file(to_square)
            if abs(from_file - to_file) == 2:
                side = "kingside" if to_file > from_file else "queenside"
                return f"Castled {side}"
        
        # Check for capture
        is_capture = board.is_capture(move)
        
        # Check for promotion
        promotion = move.promotion
        if promotion:
            promo_name = self.piece_symbols[promotion]
            if is_capture:
                return f"Pawn takes {dest} and promotes to {promo_name}"
            else:
                return f"Pawn to {dest} and promotes to {promo_name}"
        
        # Regular move or capture
        if is_capture:
            return f"{piece_name.capitalize()} takes {dest}"
        else:
            return f"{piece_name.capitalize()} to {dest}"
    
    # DEPRECATED
    def announce_move(self, move_uci: str, piece_type: int, is_capture: bool = False, 
                     is_castling: bool = False, castling_side: Optional[str] = None,
                     promotion: Optional[int] = None) -> str:
        """
        DEPRECATED: Use announce_move_from_board() instead.
        
        This method requires manually extracting move information,
        which is error-prone and duplicates logic.
        """
        # Castling
        if is_castling:
            return f"Castled {castling_side}"
        
        dest = move_uci[2:4]
        piece_name = self.piece_symbols[piece_type]
        
        if promotion:
            promo_name = self.piece_symbols[promotion]
            if is_capture:
                return f"Pawn takes {dest} and promotes to {promo_name}"
            else:
                return f"Pawn to {dest} and promotes to {promo_name}"
        
        if is_capture:
            return f"{piece_name.capitalize()} takes {dest}"
        else:
            return f"{piece_name.capitalize()} to {dest}"
    
    def announce_opponent_move(self, move_uci: str, opponent_color: str) -> str:
        """
        Announce opponent's move with color prefix.
        
        This is a lightweight version that just formats the move description.
        The caller should provide the move description using announce_move_from_board().
        
        Args:
            move_uci: Already-formatted move description (e.g., "Pawn to e4")
                     OR UCI string if you want simple format
            opponent_color: "white" or "black"
            
        Returns:
            Announcement with color prefix
        """
        color_name = opponent_color.capitalize()
        
        # If it looks like a move description, use it directly
        # Otherwise treat as UCI and create simple announcement
        if " " in move_uci or len(move_uci) > 6:
            # Already a description like "Pawn to e4"
            move_desc = move_uci
        else:
            # Simple UCI format: just announce the squares
            dest = move_uci[2:4] if len(move_uci) >= 4 else move_uci
            move_desc = f"moved to {dest}"
        
        return f"{color_name} {move_desc.lower()}"
    
    def announce_material_count(self, material_summary: dict) -> str:
        """
        Announce material count given summary from game_interface.
        
        Args:
            material_summary: Dict with keys "white", "black", "balance"
                             from GameState.material_summary()
            
        Returns:
            Material count description
        """
        balance = material_summary["balance"]
        white = material_summary["white"]
        black = material_summary["black"]
        
        # Calculate total points
        white_total = (white["pawns"] * 1 + white["knights"] * 3 + 
                      white["bishops"] * 3 + white["rooks"] * 5 + 
                      white["queens"] * 9)
        black_total = (black["pawns"] * 1 + black["knights"] * 3 + 
                      black["bishops"] * 3 + black["rooks"] * 5 + 
                      black["queens"] * 9)
        
        # Build base announcement
        if balance > 0:
            base = f"White is up by {balance} points. "
        elif balance < 0:
            base = f"Black is up by {abs(balance)} points. "
        else:
            base = "Material is equal. "
                                            
        base += f"White has {white_total} points, Black has {black_total} points."
        
        # Add notable pieces description
        details = []
        
        # White's major pieces
        white_pieces = []
        if white["queens"] > 0:
            white_pieces.append(f"{white['queens']} queen{'s' if white['queens'] > 1 else ''}")
        if white["rooks"] > 0:
            white_pieces.append(f"{white['rooks']} rook{'s' if white['rooks'] > 1 else ''}")
        
        if white_pieces:
            details.append(f"White has {', '.join(white_pieces)}")
        
        #  Black's major pieces
        black_pieces = []
        if black["queens"] > 0:
            black_pieces.append(f"{black['queens']} queen{'s' if black['queens'] > 1 else ''}")
        if black["rooks"] > 0:
            black_pieces.append(f"{black['rooks']} rook{'s' if black['rooks'] > 1 else ''}")
        
        if black_pieces:
            details.append(f"Black has {', '.join(black_pieces)}")
        
        if details:
            base += " " + ". ".join(details) + "."
        
        return base
    
    def announce_game_over(self, result: str, termination: chess.Termination | None = None) -> str:
        
        # Draw
        if result == "1/2-1/2":
            return self.format_draw_announcement(termination)
        
        # Determine winner
        if result == "1-0":
            winner = "White"
        elif result == "0-1":
            winner = "Black"
        else:
            return f"Game over. Result: {result}"
            
        # No termination reason provided
        if termination is None:
            return f"Game over. {winner} wins."
        
        # Win reasons 
        if termination == chess.Termination.CHECKMATE:
            return f"Checkmate! {winner} wins!"
        
        # TODO: Check for implementation of VARIANT_WIN and VARIANT_LOSS
        # if termination == Termination.VARIANT_WIN:
        #     return ""
        
        # if termination == Termination.VARIANT_LOSS:
        #     return ""
                
        # Resignation & timeout are not Termination enums
        # These usually come from external game state
        return f"Game over. {winner} wins."
    
    def format_draw_announcement(self, termination: chess.Termination | None = None) -> str:
        
        if termination is None:
            return "Game over. the game is a draw."
        
        if termination == chess.Termination.STALEMATE:
            return "Stalemate. The game is a draw."
        
        if termination == chess.Termination.INSUFFICIENT_MATERIAL:
            return "Draw due to insufficient material."
        
        if termination == chess.Termination.SEVENTYFIVE_MOVES:
            return "Draw by the seventy-five move rule."
        
        if termination == chess.Termination.FIFTY_MOVES:
            return "Draw by the five move rule."
        
        if termination == chess.Termination.FIVEFOLD_REPETITION:
            return "Draw by fivefold repetition."
        
        if termination == chess.Termination.THREEFOLD_REPETITION:
            return "Draw by threefold repetivion."                        
        
        # Fallback for chess.Termination.VARIANT_DRAW
        return "Game over. The game is a draw."
        
    def announce_elo_change(self, new_elo: int, change: int) -> str:
        
        if change > 0:
            return f"Your rating increased by {change} points. New rating: {new_elo}."
        elif change < 0:
            return f"Your rating decreased by {abs(change)} points. New rating: {new_elo}."
        else:
            return f"Your rating is unchanged at {new_elo}."
    
    def announce_draw_offer(self, opponent_color: str) -> str:
        color_name = opponent_color.capitalize()
        return f"{color_name} has offered a draw. Do you wish to accept the draw?"                
    
    def announce_rematch_offer(self, opponent_name: str) -> str:
        
        if opponent_name:
            return f"{opponent_name} has offered a rematch. Do you wish to accept the rematch?"
        return "Your opponent has offered a rematch. Do you wish to accept the rematch?"
    
    def announce_time_command(self, text: str, game_state: ...) -> str:
        # TODO: check where time implementation should go... 
        # if grabbed from site, or if keeping track on app
        if "opponent" in text:
            return
        elif "both" in text: 
            return
        else:
            return
    