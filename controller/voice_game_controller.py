from voice_input import intent_classifier as ic
from chess_rules import uci_converter as uc
from chess_rules.move_parse_result import MoveParseResult
from voice_output import game_announcer as ga
import threading

# TODO: Remove prints for proper logging...

class GameController:
    """
    Handles game flow, state management, and voice command processing.
    
    This controller coordinates between the chess game state, voice input/output,
    and user interactions. It manages disambiguation, game actions, and announcements.
    """
    
    def __init__(self, game, tts, board_view = None, opponent_type = "human"):
        
        self.game = game
        self.tts = tts
        self.announcer = ga.MoveAnnouncer()
        self.intent_classifier = ic.IntentClassifier()
        self.converter = uc.UCIConverter(self.game.board)
        
        # State management
        self.pending_move = None
        self.last_announcement = ""
        # TODO: Add as param or refactor based on who moves first...
        self.waiting_for_opponent = False
        self.board_view = board_view
        
        # Additional parameter that allows for testing when equals human or stockfish...
        self.opponent_type = opponent_type # Literal["human", "stockfish", "online"]
    
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
            self.tts.speak("I didn't understand that command.")
            return True
    
    def _handle_move(self, text: str) -> bool:
        """"""        
        parsed = self.converter.to_uci(text)
        
        if parsed.result == MoveParseResult.NOT_UNDERSTOOD:
            self.tts.speak("I didn't catch that. Please repeat.")
            return True
        
        if parsed.result == MoveParseResult.AMBIGUOUS:
            self.tts.speak("That move is ambiguous. Please be more specific.")
            return True
        
        if parsed.result == MoveParseResult.INVALID:
            self.tts.speak("That move is not legal.")
            return True
        
        uci = parsed.uci
        print(f"Parsed: {uci}")
        
        # Store board state before move
        board_before_move = self.game.board.copy()        
        
        # Validate and execute move
        success, error = self.game.play_move(uci)
        
        if success:             
            announcement = self.announcer.announce_move(uci, board_before_move)
            self.tts.speak(announcement)
            self.last_announcement = announcement
            # TODO: if user wants to listen to this announcement again
            # and flow continues, how does he ask for repetition?
            
            # Visualize board
            if self.opponent_type != "online":
                threading.Thread(
                    target=self.board_view.run,
                    args=(self.game,),
                    daemon=True
                ).start()
            
            # Check for check
            if self.game.board.is_check():
                self.tts.speak("Check!")
                
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
        
        if castle_result.result is None: 
            self.tts.speak("Castling is not legal in this position.")
            return True
        
        # Check if ambiguous (both side available)
        if castle_result.result == AMBIGUOUS:
            self.tts.speak("Which side? Kingisde or queenside?")
            self.pending_move = "castle"
            return True
        
        # Execute castling
        success, error = self.game.play_move(castle_result)
        
        if success:
            # TODO: Finish, maybe refactor inside gi as to recieve tuple for castle_result...
            side = ""   
            announcement = f"Castled {side}" 
            self.tts.speak(announcement)
            self.last_announcement = announcement
        else:
            self.tts.speak("Cannot castle in this position.")
        
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
            self.tts.speak(self.last_announcement)
        else:
            self.tts.speak("Nothing to repeat.")
        return True
    
    def _handle_positions(self) -> bool:
        """"""        
        piece_map = self.game.board.piece_map()
        pass
    
    def end_game(self, result: str, reason):
        announcement = self.announcer.announce_game_over(result, reason)
        self.tts.speak(announcement)
        self.last_announcement = announcement
        
        # TODO: Add Elo change announcement if available
        # if elo_change:
        #     elo_announcement = self.announcer.announce_elo_change(new_elo, change)
        #     self.tts.speak(elo_announcement)
        #     self.last_announcement = announcement
    
    def announce_opponent_move(self, move_san: str, opponent_color: str) -> None:
        """
        Announce opponent's move.
        
        Args:
            move_san: Opponent's move in SAN notation
            opponent_color: "white" or "black"
        """
        announcement = self.announcer.announce_opponent_move(move_san, opponent_color)
        self.tts.speak(announcement)
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
    
    def handle_opponent_turn(self) -> bool:
        """
        Handles opponent move lifecycle.
        
        Returns:
            False if game ended, True otherwise
        """
        # TODO: Flow takes too long between announcing player's move and saying this...
        self.tts.speak("Waiting for opponent.")
        
        # 1. Get opponent move
        if self.opponent_type != "human":
            # TODO: Set timeout based on time constraints for current game...
            # ie. blitz = 3/5 mins, rapid = 15/30/etc., bullet = 30sec etc.
            opponent_move = self.wait_for_opponent_move()

            if opponent_move is None:
                self.tts.speak("Timed out waiting for opponent.")
                return True
            
        else:           
            print("\n=== Simulating opponent move ===")
            opponent_move = input("Enter opponent's move in SAN (e.g., 'e5', 'Nf6'): ").strip()

        # 2.1 Apply opponent move
        success = self.game.play_opponent_move(opponent_move)
        
        if not success:
            # Should never get here in live games or games vs an engine...
            self.tts.speak("Opponent played an invalid move")
            return True
        
        # 2.2 Visualize opponent move
        if self.opponent_type != "online":
                threading.Thread(
                    target=self.board_view.run,
                    args=(self.game,),
                    daemon=True
                ).start()
        
        # 3. Announce opponent move
        opponent_color = "black" if self.game.player_color == "white" else "white"
        
        if not isinstance(opponent_move, str):
            opponent_move = self.game.board.san(opponent_move)
            
        self.announce_opponent_move(opponent_move, opponent_color)
        
        # 4. Check check
        if self.game.board.is_check():
            self.tts.speak("Check!")
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