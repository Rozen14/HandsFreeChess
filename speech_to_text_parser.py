import whisper
import speech_recognition as sr
import os
# TODO: Change logic for chosen mic

# ------------------------------------------------
chosen_mic = "Micrófono (Realtek HD Audio Mic input)"
os.environ["PATH"] += os.pathsep + r"C:\ffmpeg\ffmpeg-8.0.1-essentials_build\bin"
# ------------------------------------------------

# Find mic index
mic_index = 1
for index, name in enumerate(sr.Microphone.list_microphone_names()):
    if chosen_mic in name:
        mic_index = index    
    
print("Selected index:", mic_index)

if mic_index is not None:
    mic = sr.Microphone(device_index=mic_index)
else:
    mic = sr.Microphone() # Fallback to default device
    
# Test recording
r = sr.Recognizer()
with mic as source:
    r.adjust_for_ambient_noise(source)
    print("Speak...")
    audio = r.listen(source, timeout=None, phrase_time_limit=None)
    
print("Got audio: ")

wav_data = audio.get_wav_data()

with open("temp.wav", "wb") as f:
    f.write(wav_data)

# TODO: Enhance speed and accuracy (maybe train own specialized model for chess-specific commands(?))
model = whisper.load_model("small")
result = model.transcribe("temp.wav")
print("You said:", result["text"])


