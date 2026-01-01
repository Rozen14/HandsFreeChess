from voice_input import intent_classifier as ic
from voice_input import move_parser as mp
from voice_output import game_announcer as ga

# TODO: Remove prints for proper logging...
# TODO: Check if callback function (handle_speech) can be reduced (unscalable)...
# TODO: Fix flow handle_speech calls handle_clarification and so forth...

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
        else:
            self.tts.speak("I didn't understand that command.")
            return True
    
    def _handle_move(self, text: str) -> bool:
        """"""
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
            
            # Check for check
            if self.game.board.is_check():
                self.tts.speak("Check!")
                
            # Check for game over
            if self.game.is_game_over():
                result = self.game.get_result()
                # TODO: include reason as 2nd param
                result_text = self.announcer.announce_game_over(result, ...)
                self.tts.speak(result_text)
                return False
        
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
        """ """
        
        # Castling side clarification
        if self.pending_move == "castle":
            text_lower = text.lower()

        # TODO: finish...
            
        pass
    
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
        pass
    
    def announce_opponent_move(self, move_san: str, opponent_color: str) -> None:
        """"""
        announcement = self.announcer.announce_opponent_move(move_san, opponent_color)
        self.tts.speak(announcement)
        self.last_announcement = announcement
        