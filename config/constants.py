# Audio configuration
PHRASE_TIME_LIMIT = 4.0
VAD_PAUSE_THRESHOLD = 0.6
ENERGY_THRESHOLD = 150
NON_SPEAKING_DURATION = 0.4

# TTS configuration
TTS_CACHE_SIZE = 100
TTS_RATE = "+30%"
TTS_PREGEN_MOVES = 8 
BASE_DELAY = 0.4
PER_WORD_DELAY = 0.1

# TTS optimization modes
class TTSMode:
    """TTS verbosity modes for different time controls."""
    FULL = "full"           # Full announcements (classical/rapid)
    COMPACT = "compact"     # Shorter phrases (blitz)
    MINIMAL = "minimal"     # Minimal output (bullet)

# UI configuration
BOARD_SQUARE_SIZE = 80
BOARD_SIZE = 640
BOARD_FPS = 60
LIGHT_SQUARE = (240, 217, 181)
DARK_SQUARE = (181, 136, 99)

# Engine configuration
DEFAULT_SKILL_LEVEL = 10
DEFAULT_THINK_TIME = 1.0
TIMEOUT_STOCKFISH = 360

# Game mode time controls (for TTS mode selection)
TIME_CONTROLS = {
    "bullet": {"base": 60, "increment": 0, "tts_mode": TTSMode.MINIMAL},
    "blitz": {"base": 300, "increment": 0, "tts_mode": TTSMode.COMPACT},
    "rapid": {"base": 900, "increment": 0, "tts_mode": TTSMode.FULL},
    "classical": {"base": 1800, "increment": 0, "tts_mode": TTSMode.FULL},
}