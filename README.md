# HandsFreeChess
Voice-Controlled Chess Interface

A hands-free, voice-controlled accessibility tool that allows users to play chess using speech commands. The system provides audio feedback for opponent moves and game state changes, making chess more accessible for hands-free interaction.

## ⚠️ Project Status
This is an early-stage prototype currently in active development. The tool is not yet production-ready.
Features
Core Functionality

Voice-controlled move input: Say moves in natural language or algebraic notation

Natural language: "knight to e5", "pawn takes d4", "castle kingside"
Algebraic notation: "Nf3", "exd4", "O-O"
UCI notation: "e2e4", "g1f3"


Move disambiguation: Automatic clarification when moves are ambiguous

Example: If both rooks can move to e1, the system asks "Which rook: a1 or h1?"


Audio feedback: Opponent moves and game events are read aloud
Game actions: Voice commands for resign, draw offers, new games, and rematches
Local validation: Moves are validated for legality before submission

## Platform Support

Modular, platform-agnostic architecture with separate adapters
Chess.com integration (in development)
Lichess integration (planned)
Each platform integration complies with respective APIs and terms of service

## Important Clarifications
This tool does NOT include:

Chess engines or move analysis
Move evaluation or suggestions
Any form of playing assistance

All moves are entirely user-driven. The tool is designed as an accessibility aid for hands-free interaction, not a playing enhancement.

## Architecture
voice-chess-interface/
├── app/
│   └── main.py                    # Main orchestration and event loop
├── voice_input/
│   ├── speech_to_text.py          # Audio → text transcription
│   ├── intent_classifier.py       # Command intent detection
│   └── move_parser.py             # Text → chess notation parsing
├── voice_output/
│   └── text_to_speech.py          # Audio feedback generation
├── chess_rules/
│   ├── game_interface.py          # Game state management
│   └── move_validator.py          # Move validation and disambiguation
└── tests/
    └── test_move_parser.py        # Unit tests


## System Flow

### User Input

User speaks a command (e.g., "knight to e5")
Audio is captured via microphone


### Speech Processing

speech_to_text.py: Converts audio to text using Faster Whisper
intent_classifier.py: Determines command intent (move, resign, draw, etc.)
move_parser.py: Converts natural language to chess notation


### Move Validation

move_validator.py: Checks if move is legal and unambiguous
If ambiguous: System asks for clarification
If legal: Move is executed


### Move Execution

game_interface.py: Updates internal board state
Platform adapter: Submits move to chess platform API
Platform (Chess.com/Lichess) validates and processes move


### Opponent Move Feedback

System polls/streams game state from platform API
When opponent moves, text_to_speech.py announces the move
Game state changes (check, checkmate, draw offers) are also announced


### Game Completion

System announces final result
Reads Elo changes (if available)
Handles rematch offers or new game requests

## Requirements
- faster-whisper
- speech-recognition
- python-chess
- pyttsx3
- requests


## License
[License TBD]

## Disclaimer
This tool is designed as an accessibility aid for hands-free chess interaction. It does not provide move suggestions, analysis, or any form of playing assistance. All moves are user-directed, and the tool serves only to facilitate voice-based input and audio feedback.
Platform integrations comply with each platform's API terms of service. Users are responsible for ensuring their use complies with the rules and policies of their chosen chess platform.