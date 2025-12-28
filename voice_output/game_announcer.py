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
            s = f""
        elif balance < 0:
            s = f""
        else:
            s = f"Material is equal. Both sides have {...} points."
        
        pass
    
    def announce_game_over(self, result: str, reason: str = None) -> str:
        pass
    
    def format_draw_announcement(self, reason: str = None) -> str:
        pass
    
    def announce_elo_change(self, old_elo: int, new_elo: int) -> str:
        pass    
    
    def announce_draw_offer(self) -> str:
        pass
    
    def announce_rematch_offer(self) -> str:
        pass
    
    