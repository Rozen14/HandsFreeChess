from voice_input import intent_classifier as ic

intent = ic.IntentClassifier()
    
def intent_basic_move():
    examples = [
        "knight to e5",
        "pawn takes e4",
        "queen captures d5",
        "pawn h8 queen"
    ]
    assert_examples_map_to_intent(examples, "move")
    
    
def intent_castle():
    examples = [
        "castle",
        "castles queenside",
        "castle left"
    ]
    assert_examples_map_to_intent(examples, "castle")


def intent_resign():
    examples = [
        "i give up",
        "i surrender",
        "resign",
    ]
    assert_examples_map_to_intent(examples, "resign")
    
    
def intent_draw():
    examples = [
        "offer a draw",
        "that's a draw",
    ]
    assert_examples_map_to_intent(examples, "draw")
    
    
def intent_new_game():
    examples = [
        "play again", 
        "search another game",
    ]
    assert_examples_map_to_intent(examples, "new_game")
    

def intent_rematch():
    examples = [
        "offer a rematch",
        "rematch",
    ]
    assert_examples_map_to_intent(examples, "rematch")


def intent_repeat():
    examples = [
        "come again?",
        "sorry?",
        "huh?"
    ]
    assert_examples_map_to_intent(examples, "repeat")
    
    
def intent_material():
    examples = [
        "who's up?",
        "material",        
    ]
    assert_examples_map_to_intent(examples, "material")


def intent_time():
    examples = [
        "how much time left?",
        "what's the time situation?",
        "how's the clock?"
    ]
    assert_examples_map_to_intent(examples, "time")
    
    
# def intent_positions():
#     examples = [
        
#     ]
#     assert_examples_map_to_intent(examples, "positions")


def assert_examples_map_to_intent(examples: list, expected_intent: str):
    for text in examples:
        pred = intent.predict(text)
        assert pred == expected_intent, f"'{text}' → {pred} (expected {expected_intent})"


if __name__ == "__main__":
    intent_basic_move()
    intent_castle()
    intent_resign()
    intent_draw()
    intent_new_game()
    intent_rematch()
    intent_repeat()
    intent_material()
    intent_time()
    # intent_positions()
    print("All tests passed!")
    
# python -m tests.test_intent