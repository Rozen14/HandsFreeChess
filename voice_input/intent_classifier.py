from sentence_transformers import SentenceTransformer, util
from voice_input import stt_postprocessor as sttp
# TODO: Add missing intents such as time, am I in check (?), 
# current board position (?), others...
# TODO: Maybe add more colloquial examples so it can understand slang (?)

INTENT_PATTERNS = {
    "move": [
        # Standard piece moves
        "pawn to e4",
        "knight to f3",
        "bishop to c4",
        "rook to e1",
        "queen to d4",
        "king to g1",
        
        # Variations without "to"
        "pawn e4",
        "knight f3",
        "bishop c4",
        
        # Phonetic variations (what STT might produce)
        "night to f3",  # "knight" → "night"
        "night f3",
        "night to see 3",  # "c3" → "see 3"
        "night to sea 3",
        "night c3",
        "bishop b4",
        "bishop be 4",
        "bishop bee four",
        
        # Destination-only (common in casual speech)
        "e4",
        "f3",
        "c3",
        "d3",
        "d4",
        "e5",
        
        # With articles
        "pawn on to d3",  # "pawn to d3" → "on to d3"
        "pawn onto d3",
        "the pawn to e4",
        "a knight to f3",
        
        # Captures
        "pawn takes e5",
        "knight takes d4",
        "bishop takes f7",
        "take with knight",
        "capture on e5",
        
        # Common misheard patterns
        "so d3",  # "to d3" → "so d3"
        "two d3",
        "too d3",
        
        # File-only moves
        "d file",
        "e file",
        
        # With check/checkmate
        "queen to h5 check",
        "bishop to b4 check",
    ],
    
    "castle": [
        # Standard terms
        "castle",
        "castle kingside",
        "castle queenside",
        "castle short",
        "castle long",
        "kingside castle",
        "queenside castle",
        
        # Directional
        "castle left",
        "castle right",
        
        # Abbreviated
        "o-o",
        "o-o-o",
        "zero zero",
        "zero zero zero",
        
        # Common misheard (this is your issue!)
        "passel",  # "castle" → "passel"
        "cassel",
        "cassle",
        "kassel",
        "kassle",
        "pastel",
        "pascal",
        "castile",
        "castles",
        
        # With side (misheard)
        "passel kingside",
        "passel queenside",
        "cassel kingside",
        "cassel queenside",
        
        # Variations
        "castle king side",
        "castle queen side",
        "short castle",
        "long castle",
    ],
    
    "resign": [
        "resign",
        "I resign",
        "forfeit",
        "give up",
        "I give up",
        "concede",
    ],
    
    "draw": [
        "offer draw",
        "draw",
        "offer a draw",
        "request draw",
        "I want a draw",
    ],
    
    "repeat": [
        "repeat",
        "say that again",
        "what did you say",
        "repeat that",
        "again",
        "come again",
        "pardon",
    ],
    
    "new_game": [
        "new game",
        "start new game",
        "restart",
        "play again",
        "fresh game",
    ],
    
    "rematch": [
        "rematch",
        "play again",
        "another game",
        "one more game",
    ],
    
    # "positions": [
        
    # ],
    
    # "time": [
        
    # ],
}

def preprocess_text(text: str) -> str:
    """
    Preprocess text before intent classification.
    """
    return sttp.correct_stt_input(text, verbose=True)

class IntentClassifier:
    def __init__(self) -> None:
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
                
        self.intents = INTENT_PATTERNS
        
        # Pre-embed the examples 
        self.intent_embeddings = {
            intent: self.model.encode(examples, convert_to_tensor=True)
            for intent, examples in self.intents.items()
            if examples
        }
    
    def predict(self, text: str, threshold: float = 0.5) -> None | str:
        corrected_text = preprocess_text(text)
        
        text_emb = self.model.encode(corrected_text, convert_to_tensor=True)

        best_intent = None
        best_score = -1

        for intent, examples_emb in self.intent_embeddings.items():
            scores = util.cos_sim(text_emb, examples_emb)
            score = scores.max().item()

            if score > best_score:
                best_score = score
                best_intent = intent
        
        # Log confidence for debugging 
        # if best_intent and best_score > threshold:
        #     print(f"  Confidence: {best_score:.2f}")

        return best_intent if best_score > threshold else None
    