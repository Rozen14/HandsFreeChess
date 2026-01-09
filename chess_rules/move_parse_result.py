from enum import Enum, auto

class MoveParseResult(Enum):
    OK = auto()
    INVALID = auto()
    AMBIGUOUS = auto()
    NOT_UNDERSTOOD = auto()
    
from dataclasses import dataclass
@dataclass
class ParsedMove:
    result: MoveParseResult
    uci: str | None = None