"""
Predictive TTS Pre-generation

Analyzes the chess position to predict likely upcomming announcements
and pre-generates their audio in the background.
"""

import chess 
from typing import Optional


class TTSPredictor:
    """
    Predicts likely TTS phrases based on chess position.
    
    Call after each move to warm the cache for opponent's likely responses.
    """
    
    PIECE_NAMES = {
        chess.PAWN: "Pawn",
        chess.KNIGHT: "Knight",
        chess.BISHOP: "Bishop",
        chess.ROOK: "Rook",
        chess.QUEEN: "Queen",
        chess.KING: "King",
    }
    
    def __init__(self, tts):
        """
        Args:
            tts: TextToSpeech instance with pregenerate() method
        """
        self.tts = tts
        
    def predict_after_player_move(self, board: chess.Board, player_color: chess.Color):
        """
        Pre-generate likely opponent response announcements.
        
        Call this RIGHT AFTER the player makes a move.
        The opponent is about to move, so we predict their likely moves.
        
        Args:
            board: Current board state (after player's move)
            player_color: The human player's color
        """
        phrases = []
        
        opponent_color = not player_color
        color_name = "Black" if opponent_color == chess.BLACK else "White"
        
        # It's now opponent's turn - predict their moves
        legal_moves = list(board.legal_moves)
        
        # Prioritize: captures, checks, central moves
        scored_moves = []
        for move in legal_moves:
            score = 0
            
            # Captures are likely
            if board.is_capture(move):
                score += 10
            
            # Checks are important
            board.push(move)
            if board.is_check():
                score += 20
            board.pop()
            
            # Central squares are common
            dest_file = chess.square_file(move.to_square)
            dest_rank = chess.square_rank(move.to_square)
            if 2 <= dest_file <= 5 and 2 <= dest_rank <= 5:
                score += 2
            
            # Development moves in opening
            piece = board.piece_at(move.from_square)
            if piece and piece.piece_type in (chess.KNIGHT, chess.BISHOP):
                score += 3
            
            scored_moves.append((score, move))
        
        # Sort by score, take top N
        scored_moves.sort(key=lambda x: -x[0])
        top_moves = [m for _, m in scored_moves[:8]]
        
        # Generate phrases for these moves
        for move in top_moves:
            piece = board.piece_at(move.from_square)
            if not piece:
                continue
            
            piece_name = self.PIECE_NAMES.get(piece.piece_type, "Piece")
            dest = chess.square_name(move.to_square)
            
            # Build phrase
            if board.is_capture(move):
                action = f"{piece_name} takes {dest}"
            else:
                action = f"{piece_name} to {dest}"
            
            # Check for promotion
            if move.promotion:
                promo_name = self.PIECE_NAMES.get(move.promotion, "Queen")
                action += f" promotes to {promo_name}"
            
            # Full announcement
            full = f"{color_name} {action.lower()}"
            phrases.append(full)
            
            # Also generate the check variant
            board.push(move)
            if board.is_check():
                phrases.append("Check!")
            board.pop()
        
        # Always pre-generate check/checkmate
        phrases.extend(["Check!", "Checkmate!"])
        
        # Queue for background generation
        if phrases:
            self.tts.pregenerate(phrases)
            
    def predict_for_player_turn(self, board: chess.Board, player_color: chess.Color):
        """
        Pre-generate likely player move announcements.
        
        Call this when it's about to be the player's turn.
        
        Args:
            board: Current board state
            player_color: The human player's color
        """
        phrases = []
        
        # Player's legal moves
        legal_moves = list(board.legal_moves)
        
        # Score and prioritize
        scored_moves = []
        for move in legal_moves:
            score = 0
            
            if board.is_capture(move):
                score += 10
            
            board.push(move)
            if board.is_check():
                score += 15
            board.pop()
            
            # Central control
            dest_file = chess.square_file(move.to_square)
            dest_rank = chess.square_rank(move.to_square)
            if 2 <= dest_file <= 5 and 2 <= dest_rank <= 5:
                score += 2
            
            scored_moves.append((score, move))
        
        scored_moves.sort(key=lambda x: -x[0])
        top_moves = [m for _, m in scored_moves[:10]]
        
        for move in top_moves:
            piece = board.piece_at(move.from_square)
            if not piece:
                continue
            
            piece_name = self.PIECE_NAMES.get(piece.piece_type, "Piece")
            dest = chess.square_name(move.to_square)
            
            if board.is_capture(move):
                phrase = f"{piece_name} takes {dest}"
            else:
                phrase = f"{piece_name} to {dest}"
            
            if move.promotion:
                promo_name = self.PIECE_NAMES.get(move.promotion, "Queen")
                phrase += f" promotes to {promo_name}"
            
            phrases.append(phrase)
        
        # Castling phrases if available
        if board.has_kingside_castling_rights(player_color):
            phrases.append("Castled kingside")
        if board.has_queenside_castling_rights(player_color):
            phrases.append("Castled queenside")
        
        if phrases:
            self.tts.pregenerate(phrases)
    
    def integrate_predictor_with_controller(controller):
        """
        Monkey-patch the controller to add predictive pre-generation.
        
        Usage:
            controller = GameController(...)
            integrate_predictor_with_controller(controller)
        """
        predictor = TTSPredictor(controller.tts)
    
        # Store original methods
        original_handle_move = controller._handle_move
        original_handle_opponent_turn = controller.handle_opponent_turn
        
        def enhanced_handle_move(text: str) -> bool:
            result = original_handle_move(text)
            
            # After player moves, predict opponent responses
            if result:  # Game continues
                predictor.predict_after_player_move(
                    controller.game.board, 
                    controller.game.player_color
                )
            
            return result
        
        def enhanced_handle_opponent_turn() -> bool:
            result = original_handle_opponent_turn()
            
            # After opponent moves, predict player's likely moves
            if result:  # Game continues
                predictor.predict_for_player_turn(
                    controller.game.board,
                    controller.game.player_color
                )
            
            return result
        
        # Replace methods
        controller._handle_move = enhanced_handle_move
        controller.handle_opponent_turn = enhanced_handle_opponent_turn
        controller._tts_predictor = predictor
        
        return controller