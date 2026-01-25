from enum import Enum

class OpponentType(Enum):
    HUMAN = "human"
    STOCKFISH = "stockfish"
    ONLINE = "online"

class PlayerColor(Enum):
    WHITE = "white"
    BLACK = "black"

# Usage:
# if self.opponent_type == OpponentType.HUMAN:
# TODO: Implement