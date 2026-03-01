"""
Speech Planner

Orchestrates what to say and how verbose to be based on:
1. Initial time control (bullet/blitz/rapid/classical)
2. Current time remaining
3. Game phase (opening/middle/endgame)

Output: A sequence of tokens that map to cached atoms.

Verbosity Levels:
- FULL: "Black knight takes e5, check"
- NORMAL: "Knight takes e5, check"  
- COMPACT: "Knight takes e5"
- MINIMAL: "Knight e5"
- ATOMIC: "e5" (just destination in extreme time pressure)
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import List, Optional
import chess


class Verbosity(IntEnum):
    """Verbosity levels, lower = less verbose."""
    ATOMIC = 1    # Just essentials: "e5"
    MINIMAL = 2   # Piece + square: "knight e5"
    COMPACT = 3   # Add verb: "knight takes e5"
    NORMAL = 4    # Standard: "knight takes e5"
    FULL = 5      # Everything: "black knight takes e5 check"
    

@dataclass
class TimeContext:
    """Current time situation for verbosity decisions."""
    initial_time_seconds: int      # Starting time (e.g., 180 for 3+0)
    remaining_seconds: int         # Current time on clock
    increment_seconds: int = 0     # Increment per move
    opponent_remaining: int = 0    # Opponent's time (for relative pressure)
    
    @property
    def time_pressure(self) -> float:
        """
        Time pressure as 0.0 (no pressure) to 1.0 (extreme pressure).
        """
        if self.initial_time_seconds <= 0:
            return 0.0
        
        ratio = self.remaining_seconds / self.initial_time_seconds
        
        # Non-linear: pressure increases rapidly below 20%
        if ratio > 0.5:
            return 0.0
        elif ratio > 0.2:
            return (0.5 - ratio) / 0.3  # 0.0 to 1.0 as ratio goes 0.5 to 0.2
        else:
            return 1.0  # Max pressure below 20%

    @property 
    def is_bullet(self) -> bool:
        return self.initial_time_seconds <= 120  # 2 min or less
    
    @property
    def is_blitz(self) -> bool:
        return 120 < self.initial_time_seconds <= 600  # 2-10 min
    
    @property
    def is_rapid(self) -> bool:
        return 600 < self.initial_time_seconds <= 1800  # 10-30 min
    
    @property
    def is_classical(self) -> bool:
        return self.initial_time_seconds > 1800  # 30+ min


@dataclass
class SpeechPlan:
    """
    A plan for what to speak.
    
    Contains tokens that map to cached atoms, plus metadata.
    """
    tokens: List[str]           # ["knight", "takes", "e5", "check"]
    verbosity: Verbosity        # Level used for this plan
    priority: int = 0           # Higher = more important (for queue)
    interruptible: bool = True  # Can be cut short if needed
    
    def __str__(self) -> str:
        return " ".join(self.tokens)
    
    @property
    def estimated_duration_ms(self) -> float:
        """Rough estimate: ~200ms per token."""
        return len(self.tokens) * 200
    

class SpeechPlanner:
    """
    Plans speech output based on game context and time pressure.
    
    Responsibilities:
    - Convert moves to token sequences
    - Select appropriate verbosity
    - Handle special cases (castling, promotion, en passant)
    """
    
    # Base verbosity by time control
    BASE_VERBOSITY = {
        "bullet": Verbosity.MINIMAL,
        "blitz": Verbosity.COMPACT,
        "rapid": Verbosity.NORMAL,
        "classical": Verbosity.FULL,
    }
    
    PIECE_NAMES = {
        chess.PAWN: "pawn",
        chess.KNIGHT: "knight", 
        chess.BISHOP: "bishop",
        chess.ROOK: "rook",
        chess.QUEEN: "queen",
        chess.KING: "king",
    }
    
    def __init__(self, time_context: Optional[TimeContext] = None):
        """
        Args:
            time_context: Initial time context (can be updated later)
        """
        self.time_context = time_context or TimeContext(
            initial_time_seconds=600,  # Default: 10 min
            remaining_seconds=600,
        )
        self._base_verbosity = self._determine_base_verbosity()
        
    def update_time(self, remaining_seconds: int, opponent_remaining: int = 0):
        """Update current time for verbosity adjustments."""
        self.time_context.remaining_seconds = remaining_seconds
        self.time_context.opponent_remaining = opponent_remaining
    
    def set_time_control(self, initial_seconds: int, increment: int = 0):
        """Set the time control for the game."""
        self.time_context = TimeContext(
            initial_time_seconds=initial_seconds,
            remaining_seconds=initial_seconds,
            increment_seconds=increment,
        )
        self._base_verbosity = self._determine_base_verbosity()
    
    def _determine_base_verbosity(self) -> Verbosity:
        """Determine base verbosity from time control."""
        tc = self.time_context
        
        if tc.is_bullet:
            return Verbosity.MINIMAL
        elif tc.is_blitz:
            return Verbosity.COMPACT
        elif tc.is_rapid:
            return Verbosity.NORMAL
        else:
            return Verbosity.FULL
        
    def _current_verbosity(self) -> Verbosity:
        """
        Calculate current verbosity based on base + time pressure.
        
        As time pressure increases, verbosity decreases.
        """
        base = self._base_verbosity
        pressure = self.time_context.time_pressure
        
        # Reduce verbosity under pressure
        if pressure > 0.8:
            # Extreme pressure: drop 2 levels
            return Verbosity(max(Verbosity.ATOMIC, base - 2))
        elif pressure > 0.5:
            # High pressure: drop 1 level
            return Verbosity(max(Verbosity.ATOMIC, base - 1))
        else:
            return base
        
    def plan_move(
        self,
        move: chess.Move,
        board: chess.Board,  # Board state BEFORE move
        is_player_move: bool = True,
        include_color: bool = False,
    ) -> SpeechPlan:
        """
        Plan speech for a chess move.
        
        Args:
            move: The move to announce
            board: Board state BEFORE the move
            is_player_move: True if player made this move
            include_color: Include "white"/"black" prefix
            
        Returns:
            SpeechPlan with tokens
        """
        verbosity = self._current_verbosity()
        tokens: List[str] = []
        
        # Get move details
        piece = board.piece_at(move.from_square)
        if not piece:
            return SpeechPlan(tokens=["illegal"], verbosity=verbosity)
        
        piece_name = self.PIECE_NAMES[piece.piece_type]
        dest_square = chess.square_name(move.to_square)
        is_capture = board.is_capture(move)
        
        # Check for special moves
        is_castling = board.is_castling(move)
        is_en_passant = board.is_en_passant(move)
        promotion = move.promotion
        
        # Check if move gives check (need to look ahead)
        board_copy = board.copy()
        board_copy.push(move)
        gives_check = board_copy.is_check()
        gives_mate = board_copy.is_checkmate()
        board_copy.pop()
        
        # Build tokens based on verbosity
        
        # --- Handle special moves ---
        if is_castling:
            if chess.square_file(move.to_square) > chess.square_file(move.from_square):
                tokens = ["castles", "kingside"]
            else:
                tokens = ["castles", "queenside"]
            
            if gives_check and verbosity >= Verbosity.COMPACT:
                tokens.append("check")
            
            return SpeechPlan(tokens=tokens, verbosity=verbosity)
        
        # --- Regular move ---
        
        # Color prefix (only at FULL verbosity and for opponent moves)
        if include_color and verbosity >= Verbosity.FULL:
            color = "white" if piece.color == chess.WHITE else "black"
            tokens.append(color)
        
        # Piece name (skip for ATOMIC)
        if verbosity >= Verbosity.MINIMAL:
            # Skip "pawn" in compact+ modes (it's implied)
            if piece.piece_type != chess.PAWN or verbosity >= Verbosity.FULL:
                tokens.append(piece_name)
        
        # Verb (takes/to)
        if verbosity >= Verbosity.COMPACT:
            if is_capture:
                tokens.append("takes")
            elif verbosity >= Verbosity.NORMAL:
                tokens.append("to")
        
        # Destination square (always)
        tokens.append(dest_square)
        
        # En passant notation
        if is_en_passant and verbosity >= Verbosity.NORMAL:
            tokens.append("en passant")
        
        # Promotion
        if promotion:
            promo_name = self.PIECE_NAMES[promotion]
            if verbosity >= Verbosity.NORMAL:
                tokens.append("promotes to")
                tokens.append(promo_name)
            elif verbosity >= Verbosity.COMPACT:
                tokens.append(promo_name)
            # At MINIMAL/ATOMIC, skip promotion announcement
        
        # Check/checkmate suffix
        if gives_mate:
            if verbosity >= Verbosity.MINIMAL:
                tokens.append("checkmate")
        elif gives_check:
            if verbosity >= Verbosity.COMPACT:
                tokens.append("check")
        
        return SpeechPlan(tokens=tokens, verbosity=verbosity, priority=1 if gives_check else 0)
    
    def plan_opponent_move(
        self,
        move: chess.Move,
        board: chess.Board,
        opponent_color: chess.Color,
    ) -> SpeechPlan:
        """
        Plan speech for opponent's move.
        
        Includes color prefix at higher verbosity levels.
        """
        include_color = self._current_verbosity() >= Verbosity.NORMAL
        return self.plan_move(
            move=move,
            board=board,
            is_player_move=False,
            include_color=include_color,
        )
    
    def plan_error(self, error_type: str) -> SpeechPlan:
        """
        Plan speech for an error message.
        
        Args:
            error_type: "illegal", "ambiguous", "not_understood"
        """
        verbosity = self._current_verbosity()
        
        error_tokens = {
            "illegal": {
                Verbosity.FULL: ["that", "move", "is", "not", "legal"],
                Verbosity.NORMAL: ["not", "legal"],
                Verbosity.COMPACT: ["illegal"],
                Verbosity.MINIMAL: ["illegal"],
                Verbosity.ATOMIC: ["no"],
            },
            "ambiguous": {
                Verbosity.FULL: ["that", "move", "is", "ambiguous"],
                Verbosity.NORMAL: ["ambiguous"],
                Verbosity.COMPACT: ["ambiguous"],
                Verbosity.MINIMAL: ["which"],
                Verbosity.ATOMIC: ["which"],
            },
            "not_understood": {
                Verbosity.FULL: ["didn't catch that"],
                Verbosity.NORMAL: ["repeat"],
                Verbosity.COMPACT: ["repeat"],
                Verbosity.MINIMAL: ["repeat"],
                Verbosity.ATOMIC: ["repeat"],
            },
        }
        
        tokens = error_tokens.get(error_type, {}).get(verbosity, ["error"])
        return SpeechPlan(tokens=tokens, verbosity=verbosity)
    
    def plan_game_state(self, state: str) -> SpeechPlan:
        """
        Plan speech for game state announcements.
        
        Args:
            state: "check", "checkmate", "stalemate", "draw"
        """
        verbosity = self._current_verbosity()
        
        # These are always important - don't reduce too much
        state_tokens = {
            "check": ["check"],
            "checkmate": ["checkmate"],
            "stalemate": ["stalemate"],
            "draw": ["draw"],
        }
        
        tokens = state_tokens.get(state, [state])
        return SpeechPlan(
            tokens=tokens, 
            verbosity=verbosity,
            priority=2,  # High priority for game state
            interruptible=False,
        )
        
    def plan_time_announcement(self, color: str, seconds: int) -> SpeechPlan:
        """
        Plan speech for time remaining.
        
        At low verbosity, this might be skipped entirely.
        """
        verbosity = self._current_verbosity()
        
        # Skip time announcements under time pressure
        if verbosity <= Verbosity.MINIMAL:
            return SpeechPlan(tokens=[], verbosity=verbosity)
        
        if seconds >= 60:
            minutes = seconds // 60
            time_str = f"{minutes}"
            unit = "minutes" if minutes > 1 else "minute"
        else:
            time_str = f"{seconds}"
            unit = "seconds"
        
        if verbosity >= Verbosity.FULL:
            tokens = [color, "has", time_str, unit, "remaining"]
        elif verbosity >= Verbosity.NORMAL:
            tokens = [color, time_str, unit]
        else:
            tokens = [time_str, unit]
        
        return SpeechPlan(tokens=tokens, verbosity=verbosity, priority=0)
    
    
# Convenience function for quick testing
def demo_planner():
    """Demo the speech planner with various scenarios."""
    import chess
    
    # Create planner with blitz time control
    planner = SpeechPlanner()
    planner.set_time_control(300, 0)  # 5+0
    
    board = chess.Board()
    
    # Simulate some moves
    moves = ["e2e4", "e7e5", "g1f3", "b8c6", "f1b5"]
    
    print("=== Speech Planner Demo ===\n")
    
    for i, uci in enumerate(moves):
        move = chess.Move.from_uci(uci)
        is_player = i % 2 == 0
        
        plan = planner.plan_move(move, board, is_player_move=is_player)
        print(f"Move: {uci}")
        print(f"  Verbosity: {plan.verbosity.name}")
        print(f"  Tokens: {plan.tokens}")
        print(f"  Speech: \"{plan}\"")
        print()
        
        board.push(move)
    
    # Simulate time pressure
    print("=== With Time Pressure ===\n")
    planner.update_time(30)  # 30 seconds left
    
    move = chess.Move.from_uci("b5c6")  # Bxc6
    plan = planner.plan_move(move, board, is_player_move=True)
    print(f"Move: Bxc6 (30s remaining)")
    print(f"  Verbosity: {plan.verbosity.name}")
    print(f"  Tokens: {plan.tokens}")
    print(f"  Speech: \"{plan}\"")


if __name__ == "__main__":
    demo_planner()