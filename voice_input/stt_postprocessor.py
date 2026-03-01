# Multi-Layer STT Correction System

"""
Three-layer approach to handle STT errors:
1. Phonetic corrections (deterministic)
2. Chess context validation (reject non-chess words)
3. Fuzzy matching with chess vocabulary
"""

import re
from difflib import get_close_matches

# ============================================================================
# LAYER 1: Phonetic Corrections Dictionary
# ============================================================================

PHONETIC_CORRECTIONS = {
    # Pieces - CRITICAL for queen!
    "queen": "queen",
    "wean": "queen",
    "ween": "queen", 
    "weeb": "queen",
    "we": "queen",
    "qween": "queen",
    
    "knight": "knight",
    "night": "knight",
    "nite": "knight",
    "knights": "knight",
    
    "bishop": "bishop",
    "bishup": "bishop",
    "pay shump": "bishop",  # "Bd3" → "Pay shump to d3"
    "payshump": "bishop",
    
    "rook": "rook",
    "rock": "rook",
    "rue": "rook",
    
    "pawn": "pawn",
    "pond": "pawn",
    "porn": "pawn",
    "pont": "pawn",
    "pontase": "pawn",  # "Pawn takes" → "Pontase"
    
    "king": "king",
    
    # Actions
    "takes": "takes",
    "take": "takes",
    "capture": "takes",
    "captures": "takes",
    "x": "takes",
    
    # Files (letters)
    "see": "c",
    "sea": "c",
    "bee": "b",
    "be": "b",
    "dee": "d",
    "ee": "e",
    "ef": "f",
    "gee": "g",
    "aitch": "h",
    "eight": "h",
    
    # Ranks (numbers)
    "won": "1",
    "one": "1",
    "two": "2",
    "too": "2",
    "to": "2",
    "three": "3",
    "tree": "3",
    "free": "3",
    "four": "4",
    "for": "4",
    "fore": "4",
    "five": "5",
    "six": "6",
    "sicks": "6",
    "seven": "7",
    "ate": "8",
    
    # Castling
    "castle": "castle",
    "passel": "castle",
    "cassel": "castle",
    "kassle": "castle",
    
    "kingside": "kingside",
    "king side": "kingside",
    "king size": "kingside",  # "Castle King size"
    
    # Common words
    "on": "to",
    "onto": "to",
    "so": "to",
}

# ============================================================================
# LAYER 2: Chess Vocabulary (Valid Words)
# ============================================================================

CHESS_VOCABULARY = {
    # Pieces
    "queen", "knight", "bishop", "rook", "pawn", "king",
    
    # Files
    "a", "b", "c", "d", "e", "f", "g", "h",
    
    # Ranks
    "1", "2", "3", "4", "5", "6", "7", "8",
    
    # Actions
    "to", "takes", "capture", "move", "go",
    
    # Castling
    "castle", "kingside", "queenside", "short", "long",
    "o-o", "o-o-o", "left", "right",
    
    # Squares (pre-computed for efficiency)
    "a1", "a2", "a3", "a4", "a5", "a6", "a7", "a8",
    "b1", "b2", "b3", "b4", "b5", "b6", "b7", "b8",
    "c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8",
    "d1", "d2", "d3", "d4", "d5", "d6", "d7", "d8",
    "e1", "e2", "e3", "e4", "e5", "e6", "e7", "e8",
    "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8",
    "g1", "g2", "g3", "g4", "g5", "g6", "g7", "g8",
    "h1", "h2", "h3", "h4", "h5", "h6", "h7", "h8",
    
    # Common modifiers
    "check", "checkmate", "mate",
}

# ============================================================================
# LAYER 3: Pattern-Based Corrections
# ============================================================================

PATTERN_CORRECTIONS = [
    # (regex_pattern, replacement, description)
    
    # "9, set F3" → "knight f3" (weird OCR-like error)
    (r'\b9\s*,?\s*set\b', 'knight', "9 set → knight"),
    
    # "Pay shump to D3" → "bishop to d3"
    (r'\bpay\s+shump\b', 'bishop', "pay shump → bishop"),
    
    # "Pontase H3" → "pawn takes h3"
    (r'\bpontase\b', 'pawn takes', "pontase → pawn takes"),
    
    # "On takes H3" → "pawn takes h3" (assuming pawn)
    (r'\bon\s+takes\b', 'pawn takes', "on takes → pawn takes"),
    
    # "G takes H3" → "g2 takes h3" (need to infer source square)
    # This is handled in layer 4 (context)
    
    # "King size" → "kingside"
    (r'\bking\s+size\b', 'kingside', "king size → kingside"),
    
    # "Rook to be one" → "rook to b1"
    (r'\bto\s+be\s+one\b', 'to b1', "to be one → to b1"),
    
    # Common STT errors
    (r'\bknight\s+to\s+see\s+three\b', 'knight to c3', "knight to see three"),
]

# ============================================================================
# CORRECTION FUNCTIONS
# ============================================================================

def correct_stt_input(text: str, verbose: bool = True) -> str:
    """
    Apply all correction layers to STT input.
    
    Pipeline:
    1. Phonetic corrections
    2. Pattern corrections  
    3. Fuzzy matching
    4. Remove noise
    5. Normalize spacing
    
    Args:
        text: Raw STT output
        verbose: Print correction steps
        
    Returns:
        Corrected text
    """
    original = text
    words = text.lower().split()
    # Single pass: phonetic + pattern + fuzzy + noise removal
    corrected = []
    i = 0
    while i < len(words):
        # Check multi-word phonetics
        if i + 1 < len(words):
            two_words = f"{words[i]} {words[i+1]}"
            if two_words in PHONETIC_CORRECTIONS:
                corrected.append(PHONETIC_CORRECTIONS[two_words])
                i += 2
                continue
        
        word = words[i]
        # Phonetic correction
        word = PHONETIC_CORRECTIONS.get(word, word)
        # Skip noise words
        if word not in {'the', 'a', 'an', 'my', 'your'}:
            # Fuzzy match if needed
            if word not in CHESS_VOCABULARY:
                matches = get_close_matches(word, CHESS_VOCABULARY, n=1, cutoff=0.6)
                word = matches[0] if matches else word
            corrected.append(word)
        i += 1
    
    text = " ".join(corrected)
    # Apply regex patterns (only once)
    for pattern, replacement, _ in PATTERN_CORRECTIONS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # Normalize spacing (only once)
    text = re.sub(r'\b([a-h])\s+([1-8])\b', r'\1\2', text)
    
    return text