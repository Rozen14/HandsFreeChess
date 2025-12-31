from voice_input import speech_to_text as stt
from voice_input import intent_classifier as ic

mic = stt.SpeechRecognizer(mic_index=1)
print(stt.find_mic_by_index(1))
intent = ic.IntentClassifier()

# TODO: switch to listen_loop()
while True: 
    text = mic.listen_once()
    if not text: 
        continue
    print("Heard: ", text)
    print("Intent: ", intent.predict(text))
    
# python -m tests.test_manual_stt_intent