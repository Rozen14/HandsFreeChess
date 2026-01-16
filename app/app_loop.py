import time
# TODO: This will be used when implementing online play

class AppLoop:
    def __init__(self, controller, board_view=None):
        self.controller = controller
        self.board_view = board_view
        self.running = True
    
    def tick(self):
        # 1. Online opponent move check
        if self.controller.opponent_type == "online":
            self.controller.poll_online_state()
        # TODO: implement these two functions...
        # 2. UI pump (pygame)
        if self.board_view:
            self.board_view.pump_events()
        
    def run(self, tick_rate=60):
        delay = 1 / tick_rate
        while self.running:
            self.tick()
            time.sleep(delay)
            
    def stop(self):
        self.running = False