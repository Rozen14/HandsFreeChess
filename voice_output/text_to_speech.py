import pyttsx3
# TODO: (Optional) Add functions for raising/lowering volume...

class TextToSpeech:
    def __init__(self, rate=180, volume=1.0):
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", rate)
        self.engine.setProperty("volume", volume)

    def speak(self, text: str):
        self.engine.say(text)
        self.engine.runAndWait()
        
    
        