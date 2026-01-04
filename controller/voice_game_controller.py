from voice_input import intent_classifier as ic
from voice_input import move_parser as mp
from voice_output import game_announcer as ga

# TODO: Remove prints for proper logging...
# TODO: Check if callback function (handle_speech) can be reduced (unscalable)...

class GameController:
    """
    Handles game flow, state management, and voice command processing.
    
    This controller coordinates between the chess game state, voice input/output,
    and user interactions. It manages disambiguation, game actions, and announcements.
    """
    
    def __init__(self, game, tts):
        
        self.game = game
        self.tts = tts
        self.announcer = ga.MoveAnnouncer()
        self.intent_classifier = ic.IntentClassifier()
        
        # State management
        self.waiting_for_clarification = False
        self.pending_move = None
        self.last_announcement = ""
        # TODO: Add as param or refactor based on who moves first...
        self.waiting_for_opponent = False
    
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
        
        # Handle clarification mode
        if self.waiting_for_clarification:
            return self._handle_clarification(text)
        
        # Classify intent
        intent_type = self.intent_classifier.predict(text)
        print(f"Intent: {intent_type}")
        
        # Fallback: If intent is None but move_parser can parse it, assume it's a move
        if intent_type is None:
            parsed_move = mp.parse_move(text)
            if parsed_move:
                print(f"Fallback: Detected as move")
                return self._handle_move(text)
        
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
        # TODO: add self.wait_and_announce_opponent_move()
        parsed_move = mp.parse_move(text)
        
        if not parsed_move:
            self.tts.speak("Could not understand move. Please try again")
            return True
        
        print(f"Parsed: {parsed_move}")
        
        # Validate and execute move
        success, error = self.game.play_move(parsed_move)
        
        if success: 
            announcement = self.announcer.announce_move(parsed_move)
            self.tts.speak(announcement)
            self.last_announcement = announcement
            # TODO: if user wants to listen to this announcement again
            # and flow continues, how does he ask for repetition?
            
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

            # Switch to opponent's turn...
            # TODO: Implement...
            self.handle_opponent_turn()
            
        elif error == "ambiguous":
            # Enter disambiguation mode
            prompt = self.game.get_disambiguation_prompt(parsed_move)
            self.tts.speak(prompt)
            self.waiting_for_clarification = True
            self.pending_move = parsed_move
        
        else:
            self.tts.speak("That move is not legal.")
        
        return True
    
    def _handle_castling(self, text: str) -> bool:
        """"""
        castle_result = self.game.parse_castling_intent(text)
        
        if castle_result is None: 
            self.tts.speak("Castling is not legal in this position.")
            return True
        
        # Check if ambiguous (both side available)
        if castle_result == "ambiguous":
            self.tts.speak("Which side? Kingisde or queenside?")
            self.waiting_for_clarification = True
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
    
    def _handle_clarification(self, text: str) -> bool:
        """ Handle clarification responses (disambiguation or castling side)."""
        
        # Castling side clarification
        if self.pending_move == "castle":
            text_lower = text.lower()

            if any(word in text_lower for word in ["kingside", "short", "king"]):
                castle_move = "O-O"
            elif any(word in text_lower for word in ["queenside", "long", "queen"]):
                castle_move = "O-O-O"
            else:
                self.tts.speak("Please say kingside or queenside.")
                return True
                
            success, _ = self.game.play_move(castle_move)
            
            if success:
                side = "queenside" if castle_move == "O-O-O" else "kingside"
                self.tts.speak(f"Castled {side}")
            else:
                self.tts.speak("Cannot castle...")
            
            # Exit clarification mode
            self.waiting_for_clarification = False
            self.pending_move = None
            return True 
        
        from_square = mp.extract_square_disambiguation(text)
        
        # Move disambiguation clarification
        if not from_square:
            self.tts.speak("I didn't understand. Please say the square, like 'a1' or 'h8'.")                               
            return True
        
        success, _ = self.game.handle_ambiguous_move(self.pending_move, from_square)
        
        if success:
            self.tts.speak(f"Moved {self.pending_move} from {from_square}")
            
            # Exit clarification mode
            self.waiting_for_clarification = False
            self.pending_move = None
            
            # Check game state
            if self.game.is_game_over():
                # TODO: Add reason as 2nd param
                result_text = self.announcer.announce_game_over(self.game.get_result(), ...)
                self.tts.speak(result_text)
                return False
        else:
            self.tts.speak("That square doesn't match any legal move. Please try again.")
        
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
        # TODO: Utilize self.game.board.piece_map()
        piece_map = self.game.board.piece_map()
        pass
    
    def end_game(self, result: str, reason):
        announcement = self.announcer.announce_game_over(result, reason)
        self.tts.speak(announcement)
    
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
    
    # TODO: one of these two functions needs a refactor
    def wait_and_announce_opponent_move(self) -> bool:
        """
        Wait for opponent's move, then announce it.
        
        Returns:
            False if game ended, True to continue
        """
        self.waiting_for_opponent = True
        self.tts.speak("Waiting for opponent.")
        
        # Store current board state
        initial_fen = self.game.get_fen()
        
        # Poll for opponent move (simple version - checks every 2 seconds)
        import time
        max_wait = 300  # 5 minutes timeout
        elapsed = 0
        
        while elapsed < max_wait and self.waiting_for_opponent:
            time.sleep(2)
            elapsed += 2
            
            # Fetch current state (stub for now - implement platform-specific later)
            current_fen = self.game.fetch_current_state()
            
            if current_fen and current_fen != initial_fen:
                # Board changed - opponent made a move!
                opponent_move = self.game.get_last_move_san()                
                opponent_color = "black" if self.game.player_color == "white" else "white"
                
                if opponent_move:
                    self.announce_opponent_move(opponent_move, opponent_color)
                    
                    # Check for check on our king
                    if self.game.board.is_check():
                        self.tts.speak("You are in check!")
                    
                    # Check if game is over
                    if self.game.is_game_over():
                        result = self.game.get_result()
                        result_text = self.announcer.announce_game_over(result)
                        self.tts.speak(result_text)
                        self.waiting_for_opponent = False
                        return False
                
                self.waiting_for_opponent = False
                return True
        
        # Timeout
        if self.waiting_for_opponent:
            self.tts.speak("Timed out waiting for opponent.")
            self.waiting_for_opponent = False
        
        return True
    
    def handle_opponent_turn(self):
        """Test mode: manually input opponent's move."""
        print("\n=== Simulating opponent move ===")
        opponent_move = input("Enter opponent's move in SAN (e.g., 'e5', 'Nf6'): ").strip()
        
        if self.game.play_opponent_move(opponent_move):
            opponent_color = "black" if self.game.player_color == "white" else "white"
            self.announce_opponent_move(opponent_move, opponent_color)
            return True
        else:
            print("Invalid move!")
            return False