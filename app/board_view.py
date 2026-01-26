import pygame
import chess
import os
import threading
from config import constants

SQUARE_SIZE = constants.BOARD_SQUARE_SIZE
BOARD_SIZE = constants.BOARD_SIZE

LIGHT = constants.LIGHT_SQUARE
DARK = constants.DARK_SQUARE

PIECE_MAP = {
    'P': 'wp', 'N': 'wn', 'B': 'wb', 'R': 'wr', 'Q': 'wq', 'K': 'wk',
    'p': 'bp', 'n': 'bn', 'b': 'bb', 'r': 'br', 'q': 'bq', 'k': 'bk',
}
# TODO: Add game moves in SAN notation. To the right of the board
# TODO: Add way to load game and start from there for testing purposes...

class SimpleBoardVisualizer:
    """
    Board visualizer designed to run in main thread via pump_events().
    
    Usage:
        visualizer = SimpleBoardVisualizer()
        visualizer.set_game(game)
        
        # In main loop:
        while running:
            visualizer.pump_events()  # Process pygame events
            visualizer.render_if_needed()  # Draw if needed
            time.sleep(1/60)  # 60 FPS
    """
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((BOARD_SIZE, BOARD_SIZE))
        pygame.display.set_caption("HandsFreeChess")

        self.pieces = self._load_pieces()
        self.running = True
        self.needs_redraw = True
        self.game = None
        self.lock = threading.Lock()
        self._redraw_lock = threading.Lock()

    def _load_pieces(self):
        pieces = {}
        base = os.path.join("assets", "pieces")  # e.g. assets/pieces/wp.png
        for key, name in PIECE_MAP.items():
            img = pygame.image.load(os.path.join(base, f"{name}.png"))
            pieces[key] = pygame.transform.smoothscale(
                img, (SQUARE_SIZE, SQUARE_SIZE)
            )
        return pieces

    def set_game(self, game):
        """Set the game reference for the visualizer."""
        with self.lock:
            self.game = game
            self.needs_redraw = True

    def render(self):
        """Request a redraw of the board."""
        with self._redraw_lock:
            self.needs_redraw = True

    def pump_events(self):
        """
        Process pygame events (call this from main thread loop).
        Returns False if window was closed.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return False
        return True
    
    def render_if_needed(self):
        """Draw the board if redraw is needed (call from main thread loop)."""
        with self._redraw_lock:
            should_render = self.needs_redraw
            if should_render:
                self.needs_redraw = False
        
        if should_render and self.game:
            with self.lock:
                self._draw()
    
    def run(self):
        """Main pygame event loop. Should be called in main thread or started in a thread."""
        clock = pygame.time.Clock()
        
        while self.running:
            # Process pygame events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
            
            # Redraw if needed
            if self.needs_redraw and self.game:
                with self.lock:
                    self._draw()
                    self.needs_redraw = False
            
            clock.tick(constants.BOARD_FPS)  # 60 FPS
        
        self.close()

    def stop(self):
        """Stop the visualizer loop."""
        self.running = False
    
    def close(self):
        """Clean up pygame resources."""
        pygame.quit()        
        
    def _draw(self): 
        """Draw the current board state."""
        if not self.game:
            return
            
        board = self.game.board
        
        # Draw squares
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
        
        # Draw pieces
        for square, piece in board.piece_map().items():
            file = chess.square_file(square)
            rank = 7 - chess.square_rank(square)  # Flip rank for display
            self.screen.blit(
                self.pieces[piece.symbol()],
                (file * SQUARE_SIZE, rank * SQUARE_SIZE)
            )
        
        pygame.display.flip()
