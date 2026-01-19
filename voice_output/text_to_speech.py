import asyncio
import threading
import queue
import edge_tts
import tempfile
import os
import sounddevice as sd
import soundfile as sf
from typing import Optional
from pathlib import Path
import hashlib

from utils.audio_state import AudioStateManager, SpeakingContext
# TODO: Remove all prints for proper logging

class TextToSpeech:
    def __init__(
        self,
        voice: str = "en-US-GuyNeural",
        rate: str = "+20%",
        volume: str = "+0%",
        cache_dir: Optional[str] = None,
        audio_state: Optional[AudioStateManager] = None
    ):
        self.voice = voice
        self.rate = rate
        self.volume = volume
        self.audio_state = audio_state

        # Set up cache dictionary
        if cache_dir is None:
            cache_dir = os.path.join(tempfile.gettempdir(), "chess_tts_cache")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        self.queue: queue.Queue[str | None] = queue.Queue()
        self.thread = threading.Thread(
            target=self._worker,
            daemon=True
        )
        self.thread.start()
        
        # Pre-cache common phrases on startup
        self._precache_common_phrases()

    def _get_cache_path(self, text: str) -> Path:
        """
        Generate a cache file path based on text and voice settings.
        """
        # Create a unique hash for this text + voice settings
        cache_key = f"{text}_{self.voice}_{self.rate}_{self.volume}"
        file_hash = hashlib.md5(cache_key.encode()).hexdigest()
        return self.cache_dir / f"{file_hash}.wav"

    def _precache_common_phrases(self):
        """
        Pre-generate audio for common phrases.
        """
        common_phrases = [
            "Check!",
            "I didn't understand that command.",
            "I didn't catch that. Please repeat.",
            "That move is ambiguous. Please be more specific.",
            "That move is not legal.",
            "Castling is not legal in this position.",
            "Which side? Kingside or queenside?",
            "Cannot castle in this position.",
            "Nothing to repeat.",
            "Waiting for opponent.",
            "Opponent played an invalid move.",
            "Timed out waiting for opponent.",
            # Add piece movements
            "Pawn", "Knight", "Bishop", "Rook", "Queen", "King",
            "takes", "to", "and promotes to",
            "Castled kingside", "Castled queenside",
            "White", "Black",
            # Game endings
            "Checkmate!", "Stalemate.", "The game is a draw.",
            "Game over.",
        ]
        
        # Queue these for background generation
        threading.Thread(
            target=lambda: asyncio.run(self._generate_cache(common_phrases)),
            daemon=True
        ).start()
    
    async def _generate_cache(self, phrases: list[str]):
        """
        Generate cache files for a list of phrases
        """
        for phrase in phrases:
            cache_path = self._get_cache_path(phrases)
            if not cache_path.exists():
                try:
                    communicate = edge_tts.Communicate(
                        text=phrase,
                        voice=self.voice,
                        rate=self.rate,
                        volume=self.volume
                    )
                    await communicate.save(str(cache_path))
                except Exception as e:
                    print(f"Failed to cache '{phrase}': {e}")
    
    def _worker(self):
        asyncio.run(self._run())

    async def _run(self):
        while True:
            text = self.queue.get()
            if text is None:
                break

            await self._speak_once(text)
            self.queue.task_done()

    async def _speak_once(self, text: str):
        """
        Speak text, using cache if available.
        """
        # Use context manager to coordinate with STT
        context = SpeakingContext(self.audio_state) if self.audio_state else None
        
        try:
            if context:
                context.__enter__()
            
            cache_path = self._get_cache_path(text)
            
            # If cached, use the cached file
            if cache_path.exists():
                try:
                    data, samplerate = sf.read(str(cache_path), dtype="float32")
                    sd.play(data, samplerate)
                    sd.wait()
                    return
                except Exception as e:
                    print(f"Cache read failed, regenerating: {e}")
                    # Fall through to generation
            
            # Generate and cache for future use
            try: 
                communicate = edge_tts.communicate(
                    text=text,
                    voice=self.voice,
                    rate=self.rate,
                    volume=self.volume,
                )
                await communicate.save(str(cache_path))
                
                data, samplerate = sf.read(str(cache_path), dtype="float32")
                sd.play(data, samplerate)
                sd.wait()
            
            except Exception as e:
                print(f"TTS failed for '{text}': {e}")
        
        finally:
            if context:
                context.__exit__(None, None, None)

    def speak(self, text: str):
        if text:
            self.queue.put(text)

    def shutdown(self):
        self.queue.put(None)
        
    def clear_cache(self):
        """
        Clear all cached audio files.
        """
        for file in self.cache_dir.glob("*.wav"):
            file.unlink()
