from voice_output.text_to_speech import TextToSpeech
from voice_output import game_announcer as ga
import time

tts = TextToSpeech()

tts.speak("First message.")
tts.speak("Second message.")
tts.speak("Third message.")

time.sleep(12)

# python -m tests.manual_tts_test