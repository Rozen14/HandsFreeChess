import time
# TODO: This will be used when implementing online play

class AppLoop:
    """
    Main application loop that handles pygame events and game polling.
    
    This runs in the main thread and processes:
    1. Pygame events (must be in main thread on some platforms)
    2. Online game state polling (if applicable)
    3. General application tick
    """
    def __init__(self, controller, board_view=None):
        self.controller = controller
        self.board_view = board_view
        self.running = True
    
    def tick(self):
        """Single tick of the application loop."""
        # 1. Process pygame events (if visualizer exists)
        if self.board_view:
            # Returns False if window closed
            if not self.board_view.pump_events():
                self.running = False
                return
            
            # Render if needed
            self.board_view.render_if_needed()
        
        # 2. Poll online game state (if online mode)
        if self.controller.opponent_type == "online":
            # TODO: Implement online polling
            # self.controller.poll_online_state()
            pass
        
    def run(self, tick_rate=60):
        """
        Main loop.
        
        Args:
            tick_rate: Target FPS (default 60)
        """
        delay = 1 / tick_rate
        
        while self.running:
            self.tick()
            time.sleep(delay)
            
    def stop(self):
        """Stop the application loop."""
        self.running = False
        
        # Clean up visualizer
        if self.board_view:
            self.board_view.stop()
            self.board_view.close()