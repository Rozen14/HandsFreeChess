from voice_input import intent_classifier as ic
from chess_rules import uci_converter as uc
from chess_rules.chess_enums.move_parse_result import MoveParseResult
from chess_rules.chess_enums.player_type import OpponentType as OT
import chess
import time
from voice_output.speech_planner import SpeechPlanner, SpeechPlan
from voice_output.streaming_tts import StreamingTTS


# TODO: Remove prints for proper logging...

class GameController:
    """
    Handles game flow, state management, and voice command processing.
    
    This controller coordinates between the chess game state, voice input/output,
    and user interactions. It manages disambiguation, game actions, and announcements.
    """
    
    def __init__(self, game, tts: StreamingTTS, board_view = None, opponent_type: OT = OT.HUMAN, verbose: bool = False):
        self.game = game
        self.tts = tts
        self.planner = SpeechPlanner()

        self.intent_classifier = ic.IntentClassifier()
        self.converter = uc.UCIConverter(self.game.board)
        self.verbose = verbose

        # State management
        self.pending_move = None
        self.last_announcement = ""
        # TODO: Add as param or refactor based on who moves first...
        self.waiting_for_opponent = False
        self.board_view = board_view

        # Additional parameter that allows for testing when equals human or stockfish...
        self.opponent_type = opponent_type # Literal["human", "stockfish", "online"]

        if self.board_view:
            self.board_view.set_game(game)
            self.board_view.render()
        
    def handle_speech(self, text: str) -> bool:
        """
        Main speech command handler.
        
        Args:
            text: Transcribed speech text
            
        Returns:
            False to stop listening, True to continue
        """        
        if not text:
            return True
        
        print(f"You said: {text}")
        
        # Classify intent
        intent_type = self.intent_classifier.predict(text)
        print(f"Intent: {intent_type}")        
        
        # Route to appropriate handler
        if intent_type == "move":
            return self._handle_move(text)
        elif intent_type == "castle":
            return self._handle_castling(text)
        elif intent_type == "resign":
            return self._handle_resign()
        elif intent_type == "draw":
            return self._handle_draw_offer()
        elif intent_type == "new_game":
            return self._handle_new_game()
        elif intent_type == "rematch":
            return self._handle_rematch()
        elif intent_type == "repeat":
            return self._handle_repeat()
        elif intent_type == "positions":
            return self._handle_positions()
        else:
            print(f"Unrecognized intent for: {text}")
            self._speak_and_wait(self.planner.plan_error("not_understood"))
            return True
    
    def _speak_and_wait(self, plan_or_tokens, extra_delay: float = 0.0):
        """
        Speak a SpeechPlan or list of tokens and block until finished.

        Args:
            plan_or_tokens: A SpeechPlan, list of token strings, or a single string token
            extra_delay: Additional delay after playback
        """
        if isinstance(plan_or_tokens, SpeechPlan):
            self.tts.speak(plan_or_tokens, block=True)
        elif isinstance(plan_or_tokens, list):
            self.tts.speak_tokens(plan_or_tokens, block=True)
        else:
            # Single string — wrap as token list
            self.tts.speak_tokens([plan_or_tokens], block=True)

        if extra_delay > 0:
            time.sleep(extra_delay)
        
    def _handle_move(self, text: str) -> bool:
        """"""
        parsed = self.converter.to_uci(text)

        # TODO: When a move is repeated it defaults to this...
        if parsed.result == MoveParseResult.NOT_UNDERSTOOD:
            print(f"Not understood: '{text}'")
            self._speak_and_wait(self.planner.plan_error("not_understood"))
            return True

        if parsed.result == MoveParseResult.AMBIGUOUS:
            self._speak_and_wait(self.planner.plan_error("ambiguous"))
            return True

        if parsed.result == MoveParseResult.INVALID:
            print(f"Illegal move attempt: '{text}' -> '{parsed.uci}'")
            self._speak_and_wait(self.planner.plan_error("illegal"))
            return True

        uci = parsed.uci
        print(f"Parsed: {uci}")

        board_before_move = self.game.board.copy()

        # Validate and execute move
        success, error = self.game.play_move(uci)

        if success:
            move = chess.Move.from_uci(uci)
            plan = self.planner.plan_move(move, board_before_move)
            self._speak_and_wait(plan)
            self.last_announcement = str(plan)

            # Visualize board with last move highlight
            if self.board_view and self.opponent_type != OT.ONLINE:
                self.board_view.set_last_move(move)
                self.board_view.render()

            # Check for game over
            if self.game.is_game_over():
                outcome = self.game.board.outcome()
                result = outcome.result()
                reason = outcome.termination
                self.end_game(result, reason)
                return False

            # After successful move, handle opponent's turn
            return self.handle_opponent_turn()

        return True
    
    def _handle_castling(self, text: str) -> bool:
        """"""
        castle_result = self.game.parse_castling_intent(text)

        if castle_result.result == MoveParseResult.INVALID or castle_result.result == MoveParseResult.NOT_UNDERSTOOD:
            self._speak_and_wait(["castling is not legal"])
            return True

        # Check if ambiguous (both sides available)
        if castle_result.result == MoveParseResult.AMBIGUOUS:
            self._speak_and_wait(["which side"])
            self.pending_move = "castle"
            return True

        # Execute castling
        board_before_move = self.game.board.copy()
        success, error = self.game.play_move(castle_result.uci)

        if success:
            move = chess.Move.from_uci(castle_result.uci)
            plan = self.planner.plan_move(move, board_before_move)
            self._speak_and_wait(plan)
            self.last_announcement = str(plan)

            # Visualize board with last move highlight
            if self.board_view and self.opponent_type != OT.ONLINE:
                self.board_view.set_last_move(move)
                self.board_view.render()

            # Check for game over
            if self.game.is_game_over():
                outcome = self.game.board.outcome()
                result = outcome.result()
                self.end_game(result, outcome.termination)
                return False

            return self.handle_opponent_turn()
        else:
            self._speak_and_wait(["castling is not legal"])

        return True
            
    def _handle_resign(self) -> bool:
        """Handle player resignation."""
        winner = "black" if self.game.player_color == chess.WHITE else "white"
        self._speak_and_wait(["you", "resign"])
        self._speak_and_wait(["game over"])
        print(f"Player resigned. {winner} wins.")
        return False

    def _handle_draw_offer(self) -> bool:
        """Handle draw offer — against engine, auto-decline."""
        if self.opponent_type == OT.STOCKFISH:
            self._speak_and_wait(["draw", "declined"])
        else:
            # TODO: Wire up to online API or human opponent
            self._speak_and_wait(["draw", "offered"])
        return True

    def _handle_new_game(self) -> bool:
        """Signal that the player wants a new game."""
        self._speak_and_wait(["new", "game"])
        # Return False to exit the listen loop — caller should start a new game
        return False

    def _handle_rematch(self) -> bool:
        """Signal that the player wants a rematch."""
        self._speak_and_wait(["rematch"])
        # Return False to exit the listen loop — caller should start rematch
        return False
    
    def _handle_repeat(self) -> bool:
        """"""
        if self.last_announcement:
            # last_announcement is a string of tokens, split back into token list
            self._speak_and_wait(self.last_announcement.split())
        else:
            self._speak_and_wait(["nothing to repeat"])
        return True
    
    def _handle_positions(self) -> bool:
        """Announce piece positions grouped by color."""
        board = self.game.board
        piece_names = self.planner.PIECE_NAMES

        # Announce player's pieces first, then opponent's
        for color, color_name in [(self.game.player_color, "white" if self.game.player_color == chess.WHITE else "black"),
                                  (not self.game.player_color, "black" if self.game.player_color == chess.WHITE else "white")]:
            tokens = [color_name]
            for square, piece in board.piece_map().items():
                if piece.color == color:
                    name = piece_names.get(piece.piece_type, "piece")
                    sq = chess.square_name(square)
                    tokens.extend([name, sq])
            self._speak_and_wait(tokens)

        return True
    
    def end_game(self, result: str, reason):
        # Determine game state from termination reason
        if reason == chess.Termination.CHECKMATE:
            plan = self.planner.plan_game_state("checkmate")
        elif reason == chess.Termination.STALEMATE:
            plan = self.planner.plan_game_state("stalemate")
        else:
            plan = self.planner.plan_game_state("draw")

        self._speak_and_wait(plan)
        self._speak_and_wait(["game over"])
        self.last_announcement = str(plan)
    
    def announce_opponent_move(self, move_uci: str, opponent_color: str, board_before_move) -> None:
        """
        Announce opponent's move using the speech planner.

        The planner reads the board state to determine piece type and builds
        natural tokens (e.g. ["bishop", "to", "e5"]), not raw UCI strings.

        Args:
            move_uci: Opponent's move in UCI notation (e.g. "e7e5")
            opponent_color: "white" or "black"
            board_before_move: Board state before the move was applied
        """
        move = chess.Move.from_uci(move_uci)
        color = chess.WHITE if opponent_color == "white" else chess.BLACK
        plan = self.planner.plan_opponent_move(move, board_before_move, color)
        self._speak_and_wait(plan)
        self.last_announcement = str(plan)
    
    def wait_for_opponent_move(self, timeout: int = 360) -> str | None:
        """
        Blocks until opponent makes a move or timeout occurs.
        
        Returns:
            SAN move string, or None on timeout.
        """
        initial_fen = self.game.get_fen()
        elapsed = 0
        
        import time
        while elapsed < timeout:
            time.sleep(2)
            elapsed += 2
            
            current_fen = self.game.fetch_current_state()
            if current_fen and current_fen != initial_fen:
                return self.game.get_last_move_san()
        
        # TODO: Once integration has been completed, this can be refactored...
        return None
    
    def _get_manual_opponent_move(self) -> str:
        """
        Get opponent move from manual input with retry support.
        
        Returns:
            Valid UCI move string
        """
        while True:
            print("\n=== Simulating opponent move ===")
            print("Commands: UCI move (e.g., 'e7e5'), 'undo' to retry, 'quit' to exit")
            user_input = input("Enter opponent's move: ").strip().lower()
            
            # Handle special commands
            if user_input == 'quit' or user_input == 'exit':
                raise KeyboardInterrupt("User requested exit")
            
            if user_input == 'undo' or user_input == 'retry':
                print("Nothing to undo - enter a valid move.")
                continue
            
            if user_input == 'board':
                print(self.game.board)
                continue
            
            if user_input == 'legal':
                print("Legal moves:", [m.uci() for m in self.game.board.legal_moves])
                continue
            
            if user_input == 'help':
                print("Commands:")
                print("  <uci>  - Make a move (e.g., e7e5, g8f6)")
                print("  board  - Show current board")
                print("  legal  - Show legal moves")
                print("  quit   - Exit the game")
                continue
            
            # Validate the move before returning
            try:
                move = chess.Move.from_uci(user_input)
                if move in self.game.board.legal_moves:
                    return user_input
                else:
                    print(f"Invalid move: '{user_input}' is not legal in this position.")
                    print("Type 'legal' to see legal moves, or 'board' to see the board.")
            except (ValueError, AssertionError):
                print(f"Invalid UCI format: '{user_input}'")
                print("Use format like 'e7e5', 'g8f6', 'e7e8q' (for promotion)")
    
    def handle_opponent_turn(self) -> bool:
        """
        Handles opponent move lifecycle.
        
        Returns:
            False if game ended, True otherwise
        """
        # TODO: Flow takes too long between announcing player's move and saying this...
        if self.verbose:
            self._speak_and_wait(["waiting for opponent"])                
        
        # 1. Get opponent move
        if self.opponent_type == OT.HUMAN:
            # Manual input with retry support
            opponent_move = self._get_manual_opponent_move()
        else:
            # TODO: Set timeout based on time constraints for current game...
            # ie. blitz = 3/5 mins, rapid = 15/30/etc., bullet = 30sec etc.            
            opponent_move = self.wait_for_opponent_move()

            if opponent_move is None:
                self._speak_and_wait(["timed out"])
                return True
            
        board_before_move = self.game.board.copy()

        # 2.1 Apply opponent move
        success = self.game.play_opponent_move(opponent_move)
        
        if not success:
            # Should never get here in live games or games vs an engine...
            self._speak_and_wait(["not legal"])
            print(f"DEBUG: Invalid move: {opponent_move}")
            return True
        
        # 2.2 Visualize opponent move with highlight
        if self.board_view and self.opponent_type != OT.ONLINE:
            self.board_view.set_last_move(chess.Move.from_uci(opponent_move))
            self.board_view.render()
        
        # 3. Announce opponent move
        opponent_color = "black" if self.game.player_color == chess.WHITE else "white"
        
        self.announce_opponent_move(opponent_move, opponent_color, board_before_move)
        
        # 4. Check check
        if self.game.board.is_check():
            self._speak_and_wait(self.planner.plan_game_state("check"))
            return True
        
        # 5. Check game over
        if self.game.is_game_over():
            outcome = self.game.board.outcome()
            result = outcome.result()
            reason = outcome.termination
            self.end_game(result, reason)
            return False
        
        # 6. Back to player's turn
        return True