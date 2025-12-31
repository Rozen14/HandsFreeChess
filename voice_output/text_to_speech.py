import pyttsx3

class TextToSpeech:
    def __init__(self, rate=180, volume=1.0):
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", rate)
        self.engine.setProperty("volume", volume)

    def speak(self, text: str):
        self.engine.say(text)
        self.engine.runAndWait()
        
    def change_volume(self, new_volume: int): 
        self.engine.setProperty("volume", new_volume)
