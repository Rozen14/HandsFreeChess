from enum import Enum

class OpponentType(Enum):
    HUMAN = "human"
    STOCKFISH = "stockfish"
    ONLINE = "online"

# Usage:
# if self.opponent_type == OpponentType.HUMAN:
# TODO: Implement