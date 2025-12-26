from faster_whisper import WhisperModel
import speech_recognition as sr
import os
from typing import Optional, Callable
# TODO: migrate to compartmentalization, 
# add interface for microphone selection

# ------------------------------------------------
chosen_mic = "Micrófono (Realtek HD Audio Mic input)"
chosen_mic = "Micrófono externo (Realtek(R) Audio)"
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
    
r = sr.Recognizer()
model = WhisperModel(
    "Systran/faster-whisper-tiny.en", 
    device="cpu", 
    compute_type="int8",
    cpu_threads=4,
    num_workers=1
)

while True:
    with mic as source:
        r.adjust_for_ambient_noise(source)
        print("Speak...")
        audio = r.listen(source, phrase_time_limit=4)

    wav_data = audio.get_wav_data()

    with open("temp.wav", "wb") as f:
        f.write(wav_data)

    segments, info = model.transcribe(
        "temp.wav", 
        vad_filter=True, 
        vad_parameters={"min_silence_duration_ms": 250},
        beam_size=1,
        best_of=1
    )

    text = "".join(segment.text for segment in segments)
    
    if text:
        print("You said:", text)

class SpeechRecognizer:
    # TODO: Enhance speed and accuracy (maybe train own specialized model for chess-specific commands(?))
    # TODO: Change logic for chosen mic
    """
    A modular speech recognition class using Faster Whisper.
    
    Args:
        mic_index: Index of the microphone to use (None for default)
        model_name: Whisper model to use (default: "Systran/faster-whisper-tiny.en")
        device: Device to run on ("cpu" or "cuda")
        compute_type: Compute type for model ("int8", "float16", etc.)
        phrase_time_limit: Maximum seconds to listen per phrase
        vad_min_silence: Minimum silence duration in ms for VAD
    """
    
    def __init__(
        self,
        mic_index: Optional[int] = None,
        model_name: str = "Systran/faster-whisper-tiny.en",
        device: str = "cpu",
        compute_type: str = "int8",
        phrase_time_limit: float = 4,
        vad_min_silence: int = 250
    ):
        self.mic_index = mic_index
        self.phrase_time_limit = phrase_time_limit
        self.vad_min_silence = vad_min_silence
        
        # Initialize microphone
        if mic_index is not None:
            self.mic = sr.Microphone(device_index=mic_index)
        else:
            self.mic = sr.Microphone()
        
        # Initialize recognizer
        self.recognizer = sr.Recognizer()
        
        # Initialize Whisper model
        self.model = WhisperModel(
            model_name,
            device=device,
            compute_type=compute_type,
            cpu_threads=4,
            num_workers=1
        )
        
        print(f"Speech recognizer initialized with mic index: {mic_index}")
        
    def listen_once(self) -> Optional[str]:
        """
        Listen for a single phrase and return the transcribed text.
        
        Returns:
            Transcribed text or None if no speech detected
        """
        try:
            with self.mic as source:
                self.recognizer.adjust_for_ambient_noise(source)
                print("Listening...")
                audio = self.recognizer.listen(
                    source, 
                    phrase_time_limit=self.phrase_time_limit
                )
            
            # Save audio to temp file
            wav_data = audio.get_wav_data()
            with open("temp.wav", "wb") as f:
                f.write(wav_data)
            
            # Transcribe
            segments, info = self.model.transcribe(
                "temp.wav",
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": self.vad_min_silence},
                beam_size=1,
                best_of=1
            )
            
            text = "".join(segment.text for segment in segments).strip()
            return text if text else None
            
        except Exception as e:
            print(f"Error during speech recognition: {e}")
            return None
        
    def listen_loop(self, callback: Optional[Callable[[str], None]] = None):
        # TODO: Remove print when implemented
        """
        Continuously listen for speech and process it.
        
        Args:
            callback: Optional function to call with transcribed text.
                     If None, prints the text. Return False to stop loop.
        """
        while True:
            text = self.listen_once()
            
            if text:
                if callback:
                    # If callback returns False, stop the loop
                    if callback(text) == False:
                        break
                else:
                    print(f"You said: {text}")
                    
    def cleanup(self):
        """Clean up temporary files."""
        if os.path.exists("temp.wav"):
            try:
                os.remove("temp.wav")
            except Exception as e:
                print(f"Could not remove temp.wav: {e}")
    
    @staticmethod
    def list_microphones():
        """List all available microphones with their indices."""
        mics = sr.Microphone.list_microphone_names()
        for index, name in enumerate(mics):
            print(f"{index}: {name}")
        return mics
    
    @staticmethod
    def find_mic_index(mic_name: str) -> Optional[int]:
        """
        Find microphone index by name (supports partial matching).
        
        Args:
            mic_name: Full or partial name of the microphone
            
        Returns:
            Microphone index or None if not found
        """
        for index, name in enumerate(sr.Microphone.list_microphone_names()):
            if mic_name in name:
                return index
        return None