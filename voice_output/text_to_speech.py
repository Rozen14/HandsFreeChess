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
import numpy as np
import re

from utils.audio_state import AudioStateManager, SpeakingContext
# TODO: Remove all prints for proper logging

class TextToSpeech:
    def __init__(
        self,
        voice: str = "en-US-GuyNeural",
        rate: str = "+25%",
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
        
        # Memory cache for even faster playback
        self.memory_cache: dict[str, tuple[np.ndarray, int]] = {}
        
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
            # Exact error messages
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
            
            # Chunking prefixes (for fast start)
            "White", "Black",
            "White played", "Black played",
            
            # Common move components
            "Pawn", "Knight", "Bishop", "Rook", "Queen", "King",
            "takes", "to", "and promotes to",
            "Castled kingside", "Castled queenside",
            
            # Common squares - all 64 squares for completeness
            *[f"{file}{rank}" for file in "abcdefgh" for rank in "12345678"],
            
            # Most common opening moves (pre-generate full phrases)
            "Pawn to e4", "Pawn to e5", "Pawn to d4", "Pawn to d5",
            "Pawn to c4", "Pawn to c5", "Pawn to f4", "Pawn to f5",
            "Knight to f3", "Knight to c6", "Knight to f6", "Knight to c3",
            "Bishop to c4", "Bishop to g5", "Bishop to e7", "Bishop to c5",
            
            # Common captures
            "Pawn takes e5", "Pawn takes d5", "Knight takes e5",
            
            # Game endings
            "Checkmate!", "Stalemate.", "The game is a draw.",
            "Game over.",
        ]
        
        # Generate common move patterns dynamically
        pieces = ["Pawn", "Knight", "Bishop", "Rook", "Queen"]
        common_squares = ["e4", "e5", "d4", "d5", "c4", "c5", "f3", "c6", 
                         "f6", "c3", "g3", "b5", "a6", "h3"]
        
        for piece in pieces:
            for square in common_squares:
                common_phrases.append(f"{piece} to {square}")
                common_phrases.append(f"{piece} takes {square}")
        
        def generate_and_load():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            print("Pre-caching TTS phrases...")
            cached_count = 0
            loaded_count = 0
            
            for phrase in common_phrases:
                cache_path = self._get_cache_path(phrase)
                
                # Generate if not cached
                if not cache_path.exists():
                    try:
                        communicate = edge_tts.Communicate(
                            text=phrase,
                            voice=self.voice,
                            rate=self.rate,
                            volume=self.volume
                        )
                        loop.run_until_complete(communicate.save(str(cache_path)))
                        cached_count += 1
                    except Exception as e:
                        print(f"Failed to cache '{phrase}': {e}")
                        continue
                
                # Load into memory for instant playback
                try:
                    data, sr = sf.read(str(cache_path), dtype="float32")
                    self.memory_cache[phrase] = (data, sr)
                    loaded_count += 1
                except Exception as e:
                    print(f"Failed to load '{phrase}' into memory: {e}")
            
            print(f"Loaded {len(self.memory_cache)} phrases into memory cache")
        
        threading.Thread(target=generate_and_load, daemon=True).start()
    
    def _worker(self):
        asyncio.run(self._run())

    async def _run(self):
        while True:
            text = self.queue.get()
            if text is None:
                break

            await self._speak_once(text)
            self.queue.task_done()

    def _chunk_text(self, text: str) -> list[str]:
        """
        Split text into chunks for faster perceived response.
        
        Examples:
            "Black played pawn to e5" -> ["Black played", "pawn to e5"]
            "White knight takes e4" -> ["White", "knight takes e4"]
            "Pawn to e4" -> ["Pawn to e4"]  (already short, no split)
        """
        # Don't chunk if entire phrase is in memory cache (instant anyway)
        if text in self.memory_cache:
            return [text]
        
        #  Don't chunk very short phrases
        if len(text) < 15:
            return [text]
        
        # Pattern: "White/Black played <move>"
        match = re.match(r'^((?:White|Black) played)\s+(.+)$', text, re.IGNORECASE)
        if match:
            prefix = match.group(1)
            rest = match.group(2)
            # Only chunk if prefix is cached (for instant start)
            if prefix in self.memory_cache:
                return [prefix, rest]
        
        # Pattern: "White/Black <move>"
        match = re.match(r'^(White|Black)\s+(.+)$', text, re.IGNORECASE)
        if match:
            prefix = match.group(1)
            rest = match.group(2)
            # Only chunk if prefix is cached
            if prefix in self.memory_cache:
                return [prefix, rest]
        
        # Pattern: "<Piece> takes <square>"
        match = re.match(r'^(\w+)\s+(takes\s+.+)$', text, re.IGNORECASE)
        if match:
            piece = match.group(1)
            rest = match.group(2)
            # Only chunk if piece is cached
            if piece in self.memory_cache:
                return [piece, rest]
        
        # Pattern: "<Piece> to <square>"
        match = re.match(r'^(\w+)\s+(to\s+.+)$', text, re.IGNORECASE)
        if match:
            piece = match.group(1)
            rest = match.group(2)
            # Only chunk if piece is cached
            if piece in self.memory_cache:
                return [piece, rest]
        
        # Default: no chunking
        return [text]

    async def _speak_chunk(self, chunk: str) -> tuple[np.ndarray, int]:
        """
        Get audio data for a chunk (from memory, cache, or generate).
        Returns (audio_data, sample_rate)
        """
        # 1. Check memory cache (INSTANT - <10ms)
        if chunk in self.memory_cache:
            return self.memory_cache[chunk]
        
        cache_path = self._get_cache_path(chunk)
        
        # 2. Check file cache (FAST - ~50ms)
        if cache_path.exists():
            try:
                data, sr = sf.read(str(cache_path), dtype="float32")
                # Cache commonly used phrases in memory for next time
                if len(chunk) < 30: # Only cache short phrases in memory
                    self.memory_cache[chunk] = (data, sr)
                
                return (data, sr)
            except Exception as e:
                print(f"Cache read failed for '{chunk}': {e}")
        
        # 3. Generate (SLOW - ~500ms+)
        try:
            communicate = edge_tts.Communicate(
                text=chunk,
                voice=self.voice,
                rate=self.rate,
                volume=self.volume,
            )
            await communicate.save(str(cache_path))
            
            data, sr = sf.read(str(cache_path), dtype="float32")
            # Auto-cache short generated phrases
            if len(chunk) < 30:
                self.memory_cache[chunk] = (data, sr)            
            return (data, sr)
        
        except Exception as e:
            print(f"TTS generation failed for '{chunk}': {e}")
            return (np.array([]), 0)        
        
    async def _speak_once(self, text: str):
        """
        Speak text with chunking for faster percieved response.
        """
        # Use context manager to coordinate with STT
        context = SpeakingContext(self.audio_state) if self.audio_state else None
        
        try:
            if context:
                context.__enter__()
            
            # Split into chunks
            chunks = self._chunk_text(text)
            
            # If only one chunk, process normally
            if len(chunks) == 1:
                data, sr = await self._speak_chunk(chunks[0])
                if len(data) > 0:
                    sd.play(data, sr)
                    sd.wait()
                return
            
            # Multi-chunk: overlap generation and playback
            # Start playing first chunk immediately while generating second
            first_data, first_sr = await self._speak_chunk(chunks[0])
            
            if len(first_data) == 0:
                return
            
            # Start playing first chunk
            sd.play(first_data, first_sr)
            
            # Generate remaining chunks while first plays
            remaining_tasks = [self._speak_chunk(chunk) for chunk in chunks[1:]]
            remaining_chunks = await asyncio.gather(*remaining_tasks)
            
            # Wait for first chunk to finish
            sd.wait()
            
            # Play remaining chunks
            for data, sr in remaining_chunks:
                if len(data) > 0:
                    sd.play(data, sr)
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
        self.thread.join(timeout=2)
        
    def clear_cache(self):
        """
        Clear all cached audio files.
        """
        for file in self.cache_dir.glob("*.wav"):
            file.unlink()
        self.memory_cache.clear()
        
    def get_cache_stats(self) -> dict:
        """
        Get statistics about the cache.
        Useful for debugging and optimization.
        """
        file_cache_count = len(list(self.cache_dir.glob("*.wav")))
        memory_cache_count = len(self.memory_cache)
        cache_size_mb = sum(f.stat().st_size for f in self.cache_dir.glob("*.wav")) / (1024 * 1024)
        
        return {
            "file_cache_count": file_cache_count,
            "memory_cache_count": memory_cache_count,
            "cache_size_mb": round(cache_size_mb, 2)
        }