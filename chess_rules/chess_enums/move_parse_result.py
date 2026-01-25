from enum import Enum, auto

class MoveParseResult(Enum):
    """
    Ambiguous moves count as Invalid moves.
    """
    OK = auto()
    INVALID = auto()
    NOT_UNDERSTOOD = auto()
    AMBIGUOUS = auto()
    
from dataclasses import dataclass
@dataclass
class ParsedMove:
    result: MoveParseResult
    uci: str | None = None