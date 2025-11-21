import chess
import requests
import pyautogui
# TODO: Add extract_fen_from_image be it through OpenCV with a model, or python-chess, or chessboard-image-tools, etc.

class ChessBoard:
    def __init__(self):
        self.board = chess.Board()
        
    
    def update_from_fen(self, fen: str):
        """Updates the internal board state."""
        self.board.set_fen(fen)
    
    
    def play_move(self, move: str):
        """Apply a SAN or UCI move (e.g., 'Nf3' or 'g1f3')."""
        try: 
            # Try UCI first
            uci_move = chess.Move.from_uci(move)
            if uci_move in self.board.legal_moves:
                self.board.push(uci_move)
                return True
        except:
            pass
        
        # Fall back to SAN
        try:
            san_move = self.board.parse_san(move)
            self.board.push(san_move)
            return True
        except:
            return False
        # TODO: Add logic for actually making the move on site...
    
    
    def material_balance(self):
        """Returns material score for white minus black."""
        score = 0
        piece_values = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9,
        }

        for piece_type, value in piece_values.items():
            score += len(self.board.pieces(piece_type, chess.WHITE)) * value
            score -= len(self.board.pieces(piece_type, chess.BLACK)) * value

        return score
    
    
    def get_fen(self):
        return self.board.fen()
    
    
class LiChess(ChessBoard):
    def __init__(self, token):
        super().__init__()
        self.headers = {
            "Authorization": f"Bearer {token}"
        }
    
    
    def fetch_game_state(self, game_id):
        url = f"https://lichess.org/api/board/game/stream/{game_id}"
        response = requests.get(url, headers=self.headers, stream=True)

        for line in response.iter_lines():
            if line:
                event = line.decode("utf-8")
                if '"fen"' in event:
                    fen = event.split('"fen":"')[1].split('"')[0]
                    self.update_from_fen(fen)
                    return fen

        return None
        
            
class ChessDotCom(ChessBoard):
    def __init__(self, board_region):
        super().__init__()
        self.region = board_region
        
    
#     def fetch_board_from_screen(self):
#         img = pyautogui.screenshot(region=self.region)
#         img.save("board.png")
        
#         fen = extract_fen_from_image("board.png")
#         if fen:
#             self.update_from_fen(fen)
#         return fen