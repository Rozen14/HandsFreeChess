import chess
import re
from chess_rules.move_parse_result import ParsedMove, MoveParseResult

# TODO: Refactor where move_parser.py was originally used...
class UCIConverter:
    """
    Converts natural language and various chess notations to UCI.
    
    This is the ONLY place where SAN→UCI conversion happens.
    Everything else in the system uses pure UCI.
    """
    
    def __init__(self, board: chess.Board):
        """
        Initialize converter with current board state.
        
        Args:
            board: Current chess board (needed for context)
        """
        self.board = board
    
    def to_uci(self, text: str) -> ParsedMove:
        """
        Convert any chess move format to UCI.
        
        Handles:
        - Already UCI: "e2e4" → "e2e4"
        - SAN notation: "Nf3" → "g1f3"
        - Natural language: "knight to f3" → "g1f3"
        - Partial notation: "e4" → "e2e4" (finds legal move)
        
        Args:
            text: Move in any format
            
        Returns:
            ParsedMove: (
                result: MoveParseResult(enum): 
                    {
                        OK = auto()
                        INVALID = auto()
                        NOT_UNDERSTOOD = auto()
                        AMBIGUOUS = auto()
                    }, 
                uci: str | None = None
            )
        """
        text = text.strip().lower()
        
        if not text:
            return ParsedMove(MoveParseResult.NOT_UNDERSTOOD)
        
        # Check if already UCI and if legal
        if self._is_uci(text):
            if self._is_legal_uci(text):
                return ParsedMove(MoveParseResult.OK, text)
            else:
                return ParsedMove(MoveParseResult.INVALID)
        
        # If SAN, check if ambiguous
        san = text
        if self._is_ambiguous_san(san):
            return ParsedMove(MoveParseResult.AMBIGUOUS)
        
        # Convert from SAN to UCI
        uci = self._san_to_uci(text)
        if uci:
            return ParsedMove(MoveParseResult.OK, uci)
        
        # Parse natural language to SAN, then to UCI
        san = self._parse_natural_language(text)
        if san:
            if self._is_ambiguous_san(san):
                return ParsedMove(MoveParseResult.AMBIGUOUS)
            
            uci = self._san_to_uci(san)
            if uci:
                return ParsedMove(MoveParseResult.OK, uci)
        
        # Partial move (e.g., "e4", "Nf3") - find matching legal move
        uci = self._find_partial_move(text)
        if uci:
            return ParsedMove(MoveParseResult.OK, uci)
        
        # Could not parse
        return ParsedMove(MoveParseResult.NOT_UNDERSTOOD)
    
    def _is_uci(self, text: str) -> bool:
        """Check if text is valid UCI format."""
        return bool(re.fullmatch(r'[a-h][1-8][a-h][1-8][qnrb]?', text))
    
    def _san_to_uci(self, san: str) -> str | None:
        """Convert SAN to UCI using board state."""
        try:
            move = self.board.parse_san(san)
            return move.uci()
        except:
            return None
    
    def _parse_natural_language(self, text: str) -> str | None:
        """
        Parse natural language to SAN notation.
        
        Args:
            text: Natural language like "knight to e5"
            
        Returns:
            SAN notation like "Ne5", or None
        """
        # Normalize
        text = self._normalize(text)
        
        # Extract destination square
        square = self._extract_square(text)
        if not square:
            return None
        
        # Determine piece
        piece = self._extract_piece(text, square)
        
        # Check for capture
        capture = "x" if "x" in text else ""
        
        # Check for promotion
        promotion = self._extract_promotion(text)
        
        # Build SAN
        san = f"{piece}{capture}{square}"
        if promotion:
            san += f"={promotion}"
        
        return san
    
    def _find_partial_move(self, text: str) -> str | None:
        """
        Find legal move matching partial notation.
        
        For example, "e4" could match "e2e4" if it's the only legal move
        to square e4. "Nf3" matches the knight move to f3.
        
        Args:
            text: Partial move notation
            
        Returns:
            UCI of matching move, or None if ambiguous/not found
        """
        text = self._normalize(text)
        
        # Extract destination square
        square = self._extract_square(text)
        if not square:
            return None
        
        # Determine piece type
        piece_char = text[0] if text and text[0] in "kqrbn" else None
        piece_map = {'k': chess.KING, 'q': chess.QUEEN, 'r': chess.ROOK,
                     'b': chess.BISHOP, 'n': chess.KNIGHT}
        piece_type = piece_map.get(piece_char)
        
        # Find matching legal moves
        matching_moves = []
        dest_sq = chess.parse_square(square)
        
        for move in self.board.legal_moves:
            if move.to_square != dest_sq:
                continue
            
            # If piece specified, check it matches
            if piece_type:
                moving_piece = self.board.piece_at(move.from_square)
                if moving_piece and moving_piece.piece_type == piece_type:
                    matching_moves.append(move)
            else:
                # No piece specified - assume pawn
                moving_piece = self.board.piece_at(move.from_square)
                if moving_piece and moving_piece.piece_type == chess.PAWN:
                    matching_moves.append(move)
        
        # Return if exactly one match
        if len(matching_moves) == 1:
            return matching_moves[0].uci()
        
        return None  # Ambiguous or not found
    
    def _normalize(self, text: str) -> str:
        """Normalize text for parsing."""
        text = text.lower()
        
        # Fix spaced squares
        text = re.sub(r'([a-h])\s+([1-8])', r'\1\2', text)
        
        # Replacements
        replacements = {
            'captures': 'x', 'takes': 'x', 'capture': 'x', 'take': 'x',
            'move to ': '', 'go to ': '', ' to ': '', 'move ': '',
            'bishop ': 'b', 'knight ': 'n', 'rook ': 'r',
            'queen ': 'q', 'king ': 'k', 'pawn ': ''
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text
    
    def _extract_square(self, text: str) -> str | None:
        """Extract chess square from text."""
        match = re.search(r'[a-h][1-8]', text)
        return match.group(0) if match else None
    
    def _extract_piece(self, text: str, square: str) -> str:
        """
        Extract piece type from text.
        
        Handles the b-file vs bishop ambiguity.
        """
        if text.startswith(('n', 'r', 'q', 'k')):
            return text[0].upper()
        elif text.startswith('b'):
            # Ambiguity: bishop or b-file pawn?
            if square.startswith('b'):
                return ''  # b-file pawn move
            else:
                return 'B'  # Bishop move
        return ''  # Pawn
    
    def _extract_promotion(self, text: str) -> str | None:
        """Extract promotion piece from text."""
        if 'queen' in text:
            return 'Q'
        if 'rook' in text:
            return 'R'
        if 'bishop' in text:
            return 'B'
        if 'knight' in text:
            return 'N'
        
        match = re.search(r'=([qnrb])', text)
        if match:
            return match.group(1).upper()
        
        return None
    
    def _is_legal_uci(self, uci: str) -> bool:
        """
        Check if UCI move is legal
        """
        try: 
            move = chess.Move.from_uci(uci)
            return move in self.board.legal_moves
        except:
            return False
        
    def _is_ambiguous_san(self, san: str) -> bool:
        """
        Check if a SAN move is ambiguous in the current board position.

        Example:
        - "Ne5" is ambiguous if two knights can move to e5
        - "Nge2" is NOT ambiguous (already disambiguated)
        """
        try:
            # Destination square is required
            match = re.search(r'[a-h][1-8]', san)
            if not match:
                return False
            
            target_sq = match.group(0)
            
            # Piece letter (default pawn)
            piece_letter = san[0] if san[0].isupper() else ''
            
            normalized_target = f"{piece_letter}{target_sq}"
            
            matches = 0
            
            for move in self.board.legal_moves:
                try:
                    move_san = self.board.san(move)
                    
                    # Strip check/mate symbols
                    move_san = move_san.rstrip('+#!?')
                    
                    # Normalize disambiguation: Nbd2 -> Nd2, R1e1 -> Re1
                    move_san = re.sub(
                        r'^([NBRQK])([a-h1-8])x?', r'\1', move_san
                    )
                    
                    if move_san == normalized_target:
                        matches += 1
                        if matches > 1:
                            return True
                    
                except Exception:
                    continue
            
            return False
        
        except Exception:
            return False