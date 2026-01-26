from voice_input import intent_classifier as ic
from chess_rules import uci_converter as uc
from chess_rules.chess_enums.move_parse_result import MoveParseResult
from voice_output import game_announcer as ga
from chess_rules.chess_enums.player_type import OpponentType as OT
import chess
import time
from config import constants

# TODO: Remove prints for proper logging...

class GameController:
    """
    Handles game flow, state management, and voice command processing.
    
    This controller coordinates between the chess game state, voice input/output,
    and user interactions. It manages disambiguation, game actions, and announcements.
    """
    
    def __init__(self, game, tts, board_view = None, opponent_type: OT = OT.HUMAN, verbose: bool = False):
        self.game = game
        self.tts = tts
        self.announcer = ga.MoveAnnouncer()
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
            self._speak_and_wait("I didn't understand that command.")
            return True
    
    def _speak_and_wait(self, text: str, extra_delay: float = 0.0):
        """
        Speak text and wait for TTS to likely finish.
        
        This helps prevent STT from picking up TTS output.
        
        Args:
            text: Text to speak
            extra_delay: Additional delay after estimated speech time
        """
        self.tts.speak(text)
        
        # Estimate speech duration: ~100ms per word + base delay
        word_count = len(text.split())
        estimated_duration = constants.PER_WORD_DELAY * word_count + constants.BASE_DELAY + extra_delay
        
        # Wait for audio state if available, otherwise use estimated time
        if self.tts.audio_state:
            # Wait for TTS to finish (with timeout)
            self.tts.audio_state.wait_until_not_speaking(timeout=estimated_duration + 2.0)
        else:
            time.sleep(estimated_duration)
        
    def _handle_move(self, text: str) -> bool:
        """"""        
        parsed = self.converter.to_uci(text)
        
        # TODO: When a move is repeated it defaults to this...
        if parsed.result == MoveParseResult.NOT_UNDERSTOOD:
            self._speak_and_wait("I didn't catch that. Please repeat.")
            return True
        
        if parsed.result == MoveParseResult.AMBIGUOUS:
            self._speak_and_wait("That move is ambiguous. Please be more specific.")
            return True
        
        if parsed.result == MoveParseResult.INVALID:
            self._speak_and_wait("That move is not legal.")
            return True
        
        uci = parsed.uci
        print(f"Parsed: {uci}")
        
        board_before_move = self.game.board.copy()
        
        # Validate and execute move
        success, error = self.game.play_move(uci)
        
        if success:                         
            announcement = self.announcer.announce_move_from_board(uci, board_before_move)
            self._speak_and_wait(announcement)
            self.last_announcement = announcement
            # TODO: if user wants to listen to this announcement again
            # and flow continues, how does he ask for repetition?
            
            # Visualize board
            if self.board_view and self.opponent_type != OT.ONLINE:
                self.board_view.render()
            
            # Check for check
            if self.game.board.is_check():
                self._speak_and_wait("Check!")
                
            # Check for game over
            if self.game.is_game_over():
                outcome = self.game.board.outcome()
                result = outcome.result()
                # reason = outcome.termination
                reason = ... # TODO: Add fallback for resignation, timeout, leave others...          
                self.end_game(result, reason)
                return False

            # After successful move, handle opponent's turn
            return self.handle_opponent_turn()            
        
        return True
    
    def _handle_castling(self, text: str) -> bool:
        """
        
        """
        castle_result = self.game.parse_castling_intent(text)

        if castle_result.result == MoveParseResult.INVALID or castle_result.result == MoveParseResult.NOT_UNDERSTOOD: 
            self._speak_and_wait("Castling is not legal in this position.")
            return True
        
        # Check if ambiguous (both side available)
        if castle_result.result == MoveParseResult.AMBIGUOUS:
            self._speak_and_wait("Which side? Kingisde or queenside?")
            self.pending_move = "castle"
            return True
        
        # Execute castling
        success, error = self.game.play_move(castle_result.uci)
        
        if success:    
            side = castle_result.metadata.get('castling_side', '') if castle_result.metadata else ''
            
            announcement = f"Castled {side}" 
            self._speak_and_wait(announcement)
            self.last_announcement = announcement
            
            # Visualize board
            if self.board_view and self.opponent_type != "online":
                self.board_view.render()
            
            # Check for check
            if self.game.board.is_check():
                self._speak_and_wait("Check!")
                
            # Check for game over
            if self.game.is_game_over():
                outcome = self.game.board.outcome()
                result = outcome.result() 
                self.end_game(result, outcome.termination)
                return False
            
            return self.handle_opponent_turn()  
        else:
            self._speak_and_wait("Cannot castle in this position.")
        
        return True
            
    def _handle_resign(self) -> bool:
        """"""
        pass
        
    def _handle_draw_offer(self) -> bool:
        """"""
        pass
    
    def _handle_new_game(self) -> bool:
        """"""
        pass
    
    def _handle_rematch(self) -> bool:
        """"""
        pass
    
    def _handle_repeat(self) -> bool:
        """"""
        if self.last_announcement:
            self._speak_and_wait(self.last_announcement)
        else:
            self._speak_and_wait("Nothing to repeat.")
        return True
    
    def _handle_positions(self) -> bool:
        """"""        
        piece_map = self.game.board.piece_map()
        pass
    
    def end_game(self, result: str, reason):
        announcement = self.announcer.announce_game_over(result, reason)
        self._speak_and_wait(announcement)
        self.last_announcement = announcement
        
        # TODO: Add Elo change announcement if available
        # if elo_change:
        #     elo_announcement = self.announcer.announce_elo_change(new_elo, change)
        #     self._speak_and_wait(elo_announcement)
        #     self.last_announcement = announcement
    
    def announce_opponent_move(self, move_uci: str, opponent_color: str, board_before_move) -> None:
        """
        Announce opponent's move.
        
        Args:
            move_san: Opponent's move in UCI notation
            opponent_color: "white" or "black"
        """        
        move_uci = self.announcer.announce_move_from_board(move_uci, board_before_move)
        announcement = self.announcer.announce_opponent_move(move_uci, opponent_color)
        self._speak_and_wait(announcement)
        self.last_announcement = announcement
    
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
            self._speak_and_wait("Waiting for opponent.")                
        
        # 1. Get opponent move
        if self.opponent_type == OT.HUMAN:
            # Manual input with retry support
            opponent_move = self._get_manual_opponent_move()
        else:
            # TODO: Set timeout based on time constraints for current game...
            # ie. blitz = 3/5 mins, rapid = 15/30/etc., bullet = 30sec etc.            
            opponent_move = self.wait_for_opponent_move()

            if opponent_move is None:
                self._speak_and_wait("Timed out waiting for opponent.")
                return True
            
        board_before_move = self.game.board.copy()

        # 2.1 Apply opponent move
        success = self.game.play_opponent_move(opponent_move)
        
        if not success:
            # Should never get here in live games or games vs an engine...
            self._speak_and_wait("Opponent played an invalid move")
            print(f"DEBUG: Invalid move: {opponent_move}")
            return True
        
        # 2.2 Visualize opponent move
        if self.board_view and self.opponent_type != OT.ONLINE:
            self.board_view.render()
        
        # 3. Announce opponent move
        opponent_color = "black" if self.game.player_color == chess.WHITE else "white"
        
        self.announce_opponent_move(opponent_move, opponent_color, board_before_move)
        
        # 4. Check check
        if self.game.board.is_check():
            self._speak_and_wait("Check!")
            return True
        
        # 5. Check game over
        if self.game.is_game_over():
                outcome = self.game.board.outcome()
                result = outcome.result()
                # reason = outcome.termination
                reason = ... # TODO: Add fallback for resignation, timeout, leave others...          
                self.end_game(result, reason)
                return False
        
        # 6. Back to player's turn
        return True