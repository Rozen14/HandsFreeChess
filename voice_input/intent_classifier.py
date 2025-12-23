from sentence_transformers import SentenceTransformer, util

class IntentClassifier:
    def __init__(self) -> None:
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
                
        self.intents = {
            "castle": [
                "castle",
                "castle kingside",
                "castle queenside",
                "short castle",
                "long castle",
            ],
            "move": [
                # Natural language patterns (diverse phrasing)
                "knight to e5",
                "pawn takes e4",
                "move the rook to a7",
                "bishop captures on f3",
                "promote to queen",
                # Algebraic/UCI patterns
                "knight f3",
                "e2 e4",
                "e7 e8 queen",
            ],
            "resign": [
                "resign",
                "I give up",
                "forfeit the game",
            ],
            "draw": [
                "offer a draw",
                "propose draw",
                "I want a draw",
            ],
            "new_game": [
                "new game",
                "start a new game",
                "let's play again",
            ],
            "rematch": [
                "rematch",
                "run it back",
                "one more game",
            ],
            "repeat": [
                "repeat that",
                "what did you say",
                "say it again",
            ],            
        }
        
        # Pre-embed the examples 
        self.intent_embeddings = {
            intent: self.model.encode(examples, convert_to_tensor=True)
            for intent, examples in self.intents.items()
        }
    
    def predict(self, text: str, threshold: float = 0.5) -> None | str:
        text_emb = self.model.encode(text, convert_to_tensor=True)

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
    