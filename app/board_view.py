import pygame
import chess
import os

SQUARE_SIZE = 80
BOARD_SIZE = 8 * SQUARE_SIZE

LIGHT = (240, 217, 181)
DARK = (181, 136, 99)

PIECE_MAP = {
    'P': 'wp', 'N': 'wn', 'B': 'wb', 'R': 'wr', 'Q': 'wq', 'K': 'wk',
    'p': 'bp', 'n': 'bn', 'b': 'bb', 'r': 'br', 'q': 'bq', 'k': 'bk',
}


class SimpleBoardVisualizer:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((BOARD_SIZE, BOARD_SIZE))
        pygame.display.set_caption("HandsFreeChess")

        self.pieces = self._load_pieces()
        self.running = True
        self.needs_redraw = True

    def _load_pieces(self):
        pieces = {}
        base = os.path.join("assets", "pieces")  # e.g. assets/pieces/wp.png
        for key, name in PIECE_MAP.items():
            img = pygame.image.load(os.path.join(base, f"{name}.png"))
            pieces[key] = pygame.transform.smoothscale(
                img, (SQUARE_SIZE, SQUARE_SIZE)
            )
        return pieces

    def render(self):
        self.needs_redraw = True

    def run(self, game):
        clock = pygame.time.Clock()
        
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                
            if self.needs_redraw:
                self._draw(game)
                self.needs_redraw = False
            
            clock.tick(60)

    def stop(self):
        self.running = False
    
    def close(self):
        pygame.quit()        
        
    def _draw(self, game): 
        board = game.board
        
        for rank in range(8):
            for file in range(8):
                color = LIGHT if (rank + file) % 2 == 0 else DARK
                pygame.draw.rect(
                    self.screen,
                    color,
                    pygame.Rect(
                        file * SQUARE_SIZE,
                        rank * SQUARE_SIZE,
                        SQUARE_SIZE,
                        SQUARE_SIZE
                    )
                )
        
        for square, piece in board.piece_map().items():
            file = chess.square_file(square)
            rank = 7 - chess.square_rank(square)
            self.screen.blit(
                self.pieces[piece.symbol()],
                (file * SQUARE_SIZE, rank * SQUARE_SIZE)
            )
        
        pygame.display.flip()
        
