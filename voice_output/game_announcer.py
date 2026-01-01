import re 
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
        
        # Castling
        if move == "O-O":
            return ""
        if move == "O-O-O":
            return ""
        
        
        
        pass
    
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
    
    def announce_game_over(self, result: str, reason: str = None) -> str:
        
        pass
    
    def format_draw_announcement(self, reason: str = None) -> str:
        
        pass
    
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
        
    def announce_opponent_move(self, move_san: str, opponent_color: str) -> str:
        # TODO: implement
        pass
    