import re 
from chess import Termination
from typing import Optional
# TODO: Finish...

class MoveAnnouncer:
    """
    Converts chess moves and game data into natural language announcements.
    
    This class works with strings and simple data types, not chess objects.
    All chess logic should remain in chess_rules/ modules.
    """
    
    def __init__(self):
        self.piece_symbols = {
            "K": "king",
            "Q": "queen",
            "R": "rook",
            "B": "bishop",
            "N": "knight",
            "": "pawn"
        }    
    
    def announce_move(self, move: str) -> str:
        # TODO: implement fallback in case move comes in uci format
        move = move.strip()
        
        # Remove check/checkmate indicators for cleaner announcement
        move = move.replace('+', '').replace('#', '')
        
        # Castling
        if move == "O-O":
            return ""
        if move == "O-O-O":
            return ""
        
        # Check for promotion (e.g., "e8=Q")
        promo_match = re.search(r'=([QRBN])', move)
        promotion = None
        if promo_match:
            promotion = self.piece_symbols[promo_match.group(1)]
            move = move[:promo_match.start()] # Remove promotion part
        
        # Check for capture
        is_capture = 'x' in move
        move = move.replace('x', '')
        
        # Extract piece type (first character if uppercase, else pawn)
        if move and move[0].isupper():
            piece = self.piece_symbols.get(move[0], 'piece')
            move = move[1:] # Remove piece symbol
        else:
            piece = 'pawn'
        
        # Extract destination square (last 2 characters)
        square_match = re.search(r'[a-h][1-8]', move)
        if not square_match:
            return "Invalid move"
        
        dest_square = square_match.group(0)
        
        # Build announcement
        if promotion:
            if is_capture:
                return f"Pawn takes {dest_square} and promotes to {promotion}"
            else:
                return f"Pawn to {dest_square} and promotes to {promotion}"
        elif is_capture:
            return f"{piece.capitalize()} takes {dest_square}"
        else:
            return f"{piece.capitalize()} to {dest_square}"
    
    def announce_opponent_move(self, move_san: str, opponent_color: str) -> str:
        # TODO: implement
        color_name = opponent_color.capitalize()
        move_desc = self.announce_move(move_san)
        return f"{color_name} played {move_desc.lower()}"
    
    def announce_material_count(self, white_material: dict, black_material: dict, balance: int) -> str:
        
        if balance > 0:
            s = f"White is up by {...}"
        elif balance < 0:
            s = f"Black is up by {...}"
        else:
            s = f"Material is equal. Both sides have {...} points."
        
        # TODO: Add descriptive data of important pieces each side has
        # ie. black has 2 rooks and a bishop, pawn has a queen, down 2 pawns...
        s += f"{...}"
        return s
    
    def announce_game_over(self, result: str, termination: Termination | None = None) -> str:
        
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
        if termination == Termination.CHECKMATE:
            return f"Checkmate! {winner} wins!"
        
        # TODO: Check for implementation of VARIANT_WIN and VARIANT_LOSS
        # if termination == Termination.VARIANT_WIN:
        #     return ""
        
        # if termination == Termination.VARIANT_LOSS:
        #     return ""
                
        # Resignation & timeout are not Termination enums
        # These usually come from external game state
        return f"Game over. {winner} wins."
    
    def format_draw_announcement(self, termination: Termination | None = None) -> str:
        
        if termination is None:
            return "Game over. the game is a draw."
        
        if termination == Termination.STALEMATE:
            return "Stalemate. The game is a draw."
        
        if termination == Termination.INSUFFICIENT_MATERIAL:
            return "Draw due to insufficient material."
        
        if termination == Termination.SEVENTYFIVE_MOVES:
            return "Draw by the seventy-five move rule."
        
        if termination == Termination.FIFTY_MOVES:
            return "Draw by the five move rule."
        
        if termination == Termination.FIVEFOLD_REPETITION:
            return "Draw by fivefold repetition."
        
        if termination == Termination.THREEFOLD_REPETITION:
            return "Draw by threefold repetivion."                        
        
        # Fallback for Termination.VARIANT_DRAW
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
