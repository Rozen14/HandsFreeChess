from sentence_transformers import SentenceTransformer, util
# TODO: Check if intents dict can be reduced...

class IntentClassifier:
    def __init__(self) -> None:
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        
        self.intents = {
            "castle_kingside": [
                "castle kingside", "castle short", "short castle",
                "small castle", "king side castle"
            ],
            "castle_queenside": [
                "castle queenside", "castle long", "long castle",
                "big castle", "queen side castle"
            ],
            "castle_generic": [
                "castle", "castles", "do castling", "perform castling", 
                "castle left", "castle right"            
            ],
            "en_passant": [
                "en passant", "take en passant", "pawn takes en passant",
                "capture en passant", "ep capture", "ep"
            ],
            "promotion": [
                "promote to queen", "promote to rook", "promote to knight",
                "promote to bishop", "i want a queen", "turn into a queen"
            ],
            "move": [
                "knight to e5", "pawn takes e4", "queen captures d5",
                "move rook to a7", "bishop takes on f3", "move pawn", 
                "bishop captures", "pawn to e8", "pawn promotes"
            ],
            "uci_move": [
                "e2e4", "g1f3", "b7b8q", "a2a1r", "h2h1n", "e7e8q"
            ],
            "resign": [
                
            ],
            "draw": [
                
            ],
            "new_game": [
                
            ],
            "rematch": [
                
            ],
            "repeat": [
                
            ],
            
        }
        
        # Pre-embed the examples 
        self.intent_embeddings = {
            intent: self.model.encode(examples, convert_to_tensor=True)
            for intent, examples in self.intents.items()
        }
    
    def predict(self, text) -> None | str:
        text_emb = self.model.encode(text, convert_to_tensor=True)

        best_intent = None
        best_score = 0

        for intent, examples_emb in self.intent_embeddings.items():
            scores = util.cos_sim(text_emb, examples_emb)
            score = scores.max().item()

            if score > best_score:
                best_score = score
                best_intent = intent

        return best_intent if best_score > 0.45 else None
        