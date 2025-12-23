import re
# TODO: (Optional) make parser more strict (ie. detecting invalid promotions, 
# producing promotions only when user says 'promote', etc.)
# TODO: check if replacements dict can be reduced

# ---------------------------------------------------------
# Normalize generic commands (excluding castling)
# ---------------------------------------------------------
def normalize_command(text) -> str:
    text = text.lower()
    
    # fix spaced squares: “e 5”, “d   4”
    text = re.sub(r"([a-h])\s+([1-8])", r"\1\2", text)
    
    replacements = {
        "takes": "x",
        "captures": "x",
        "take": "x",
        "capture": "x",
        "pawn to ": "",
        "move ": "",
        "go to ": "",
        "bishop ": "b",
        "knight ": "n",
        "rook ": "r",
        "queen ": "q",
        "king ": "k"
    }
    
    for k, v in replacements.items():
        text = text.replace(k, v)

    return text


# ---------------------------------------------------------
# Promotion extraction
# ---------------------------------------------------------
def extract_promotion(text) -> str | None:
    # full words
    if "queen" in text: return "Q"
    if "rook" in text: return "R"
    if "bishop" in text: return "B"
    if "knight" in text: return "N"

    # short form: =q or =n
    m = re.search(r"=([qnrb])", text)
    if m:
        return m.group(1).upper()

    return None


# ---------------------------------------------------------
# Basic square extraction
# ---------------------------------------------------------
def extract_square(text: str) -> str | None:
    match = re.search(r"[a-h][1-8]", text)
    return match.group(0) if match else None

def extract_square_disambiguation(text: str) -> str | None:
    text_lower = text.lower().strip()
    match = extract_square(text_lower)
    if match:
        return match
    
    number_words = {
        'one': '1', 'two': '2', 'three': '3', 'four': '4',
        'five': '5', 'six': '6', 'seven': '7', 'eight': '8'
    }
    
    for word, digit in number_words.items():
        # Match patterns like "a one", "h eight"
        pattern = r'([a-h])\s+' + word + r'\b'
        match = re.search(pattern, text_lower)
        if match:
            return f"{match.group(1)}{digit}"
    
    return None


# ---------------------------------------------------------
# Main move parser combining all logic
# ---------------------------------------------------------
def parse_move(text) -> None | str:   
    raw_text = text.strip().lower()
    
    # Detect UCI notation: exactly 4 or 5 chars.
    m = re.fullmatch(r"([a-h][1-8])([a-h][1-8])([qnrb])?", raw_text)
    if m:
        from_sq = m.group(1)
        to_sq = m.group(2)
        promo = m.group(3)
        if promo:
            promo = promo.upper()
            return f"{from_sq}{to_sq}={promo}"
        return f"{from_sq}{to_sq}"
    
    # If not UCI (SAN)
    text = normalize_command(text)

    # extract target square
    square = extract_square(text)
    if not square:
        return None

    # determine piece
    if text.startswith(("b","n","r","q","k")):
        piece = text[0].upper()
    else:
        piece = ""   # pawn

    # capture?
    capture = "x" if "x" in text else ""

    # promotion?
    promotion = extract_promotion(text)

    move = f"{piece}{capture}{square}"
    if promotion:
        move += f"={promotion}"

    return move
