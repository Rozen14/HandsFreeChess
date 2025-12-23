from voice_input import move_parser as mp

# SAN testing
def test_basic_move():
    assert mp.parse_move("knight to e5") == "Ne5"


def test_capture():
    assert mp.parse_move("pawn takes e4") == "xe4"

    
def test_promotion():
    assert mp.parse_move("pawn e8 queen") == "e8=Q" 


# UCI testing
def test_basic_move_UCI():
    assert mp.parse_move("e2e4") == "e2e4"

    
def test_promotion_UCI():
    assert mp.parse_move("e7e8q") == "e7e8=Q"


if __name__ == "__main__":
    test_basic_move()
    test_capture()
    test_promotion()
    test_basic_move_UCI()    
    test_promotion_UCI()
    print("All tests passed!")
    
# python -m tests.test_move_parser