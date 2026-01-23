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
import time
from collections import OrderedDict

from utils.audio_state import AudioStateManager, SpeakingContext
# TODO: Remove all prints for proper logging
# TODO: Migrate from .wav into in-memory audio buffers

class TextToSpeech:
    def __init__(
        self,
        voice: str = "en-US-GuyNeural",
        rate: str = "+30%",
        volume: str = "+0%",
        cache_dir: Optional[str] = None,
        audio_state: Optional[AudioStateManager] = None,
        enable_chunking: bool = False 
    ):
        self.voice = voice
        self.rate = rate
        self.volume = volume
        self.audio_state = audio_state
        self.enable_chunking = enable_chunking

        # Set up cache dictionary
        if cache_dir is None:
            cache_dir = os.path.join(tempfile.gettempdir(), "chess_tts_cache")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Memory cache for even faster playback
        self.max_cache_size = 50
        self.memory_cache: dict[str, tuple[np.ndarray, int]] = {}
        self.memory_cache = OrderedDict() # LRU eviction
        self._cache_lock = threading.Lock()  # ADD THIS
        
        # Standard sample rate for consistency
        self.target_sample_rate = 24000
        
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
            
            # Most common full phrases
            "Pawn to e4", "Pawn to e5", "Pawn to d4", "Pawn to d5",
            "Pawn to c4", "Pawn to c5", "Knight to f3", "Knight to c6",
            "Bishop to c4", "Bishop to g5", "Knight to f6", "Bishop to e7",
            
            # Chunking prefixes (for fast start)
            "White", "Black",
            "White played", "Black played",
            
            # Common opponent moves
            "Black pawn to e5", "Black pawn to c5", "Black knight to f6",
            "Black pawn to d5", "Black knight to c6", "Black bishop to e7",
            "White pawn to e4", "White pawn to d4", "White knight to f3",
            "White bishop to c4", "White knight to c3",
            
            # Game endings
            "Checkmate!", "Stalemate.", "The game is a draw.",
            "Game over.",
        ]
        
        def _add_to_cache(self, phrase: str, data: tuple):
            if len(self.memory_cache) >= self.max_cache_size:
                self.memory_cache.popitem(last=False)  # Remove oldest
            self.memory_cache[phrase] = data
        
        def generate_and_load():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            print("Pre-caching TTS phrases...")
            success_count = 0
            
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
                        # Small delay to avoid overwhemling edge-tts
                        time.sleep(0.1)
                    except Exception as e:
                        print(f"Failed to cache '{phrase}': {e}")
                        continue
                
                # Validate and load into memory                
                try:
                    if cache_path.stat().st_size < 1000: # File too small, likely corrupted
                        print(f"Corrupted cache for '{phrase}', regenerating...")
                        cache_path.unlink()
                        continue
                    
                    data, sr = sf.read(str(cache_path), dtype="float32")
                    
                    # Resample if needed for consistency
                    if sr != self.target_sample_rate:
                        import scipy.signal
                        num_samples = int(len(data) * self.target_sample_rate / sr)
                        data = scipy.signal.resample(data, num_samples)
                        sr = self.target_sample_rate
                    
                    # Normalize audio to prevent clipping
                    if len(data) > 0:
                        max_val = np.abs(data).max()
                        if max_val > 0:
                            data = data / max_val * 0.95
                        
                    _add_to_cache(phrase, (data, sr))
                    success_count += 1
                
                except Exception as e:
                    print(f"Failed to load '{phrase}': {e}")
                    # Delete corrupted cache file
                    if cache_path.exists():
                        try:
                            cache_path.unlink()
                        except:
                            pass
                    
            print(f"TTS cache ready: {success_count}/{len(common_phrases)} phrases loaded")
        
        threading.Thread(target=generate_and_load, daemon=True).start()
    
    def _worker(self):
        asyncio.run(self._run())

    async def _run(self):
        while True:
            text = self.queue.get()
            if text is None:
                break

            await self._speak_once_async(text)
            self.queue.task_done()

    async def _speak_chunk(self, chunk: str) -> tuple[np.ndarray, int]:
        """
        Get audio data for a chunk (from memory, cache, or generate).
        Returns (audio_data, sample_rate)
        """
        # 1. Check memory cache (INSTANT)
        with self._cache_lock:
            if chunk in self.memory_cache:
                return self.memory_cache[chunk]
        
        cache_path = self._get_cache_path(chunk)
        
        # 2. Check file cache 
        if cache_path.exists():
            try:
                # Validate file size
                if cache_path.stat().st_size < 1000:
                    cache_path.unlink()
                    raise Exception("Corrupted cache file")
                
                data, sr = sf.read(str(cache_path), dtype="float32")
                
                # Resample if needed
                if sr != self.target_sample_rate:
                    import scipy.signal
                    num_samples = int(len(data) * self.target_sample_rate / sr)
                    data = scipy.signal.resample(data, num_samples)
                    sr = self.target_sample_rate
                
                # Normalize
                if len(data) > 0:
                    max_val = np.abs(data).max()
                    if max_val > 0:
                        data = data / max_val * 0.95

                return (data, sr)
            except Exception as e:
                print(f"Cache read failed for '{chunk}': {e}")
        
        # 3. Generate 
        try:
            communicate = edge_tts.Communicate(
                text=chunk,
                voice=self.voice,
                rate=self.rate,
                volume=self.volume,
            )
            await communicate.save(str(cache_path))
            
            # Validate generated file
            if cache_path.stat().st_size < 1000:
                raise Exception("Generated file too small")
            
            data, sr = sf.read(str(cache_path), dtype="float32")
            
            # Resample and normalize
            if sr != self.target_sample_rate:
                import scipy.signal
                num_samples = int(len(data) * self.target_sample_rate / sr)
                data = scipy.signal.resample(data, num_samples)
                sr = self.target_sample_rate
            
            if len(data) > 0:
                max_val = np.abs(data).max()
                if max_val > 0:
                    data = data / max_val * 0.95
            
            return (data, sr)
        
        except Exception as e:
            print(f"TTS generation failed for '{chunk}': {e}")
            return (np.array([]), 0)    
        
    def _play_audio_sync(self, data: np.ndarray, sr: int):
        """
        Play audio synchronously with proper coordination
        """
        context = SpeakingContext(self.audio_state) if self.audio_state else None
        
        try:
            if context:
                context.__enter__()
                
            if len(data) == 0:
                return
            
            sd.play(data, sr)
            sd.wait()
            time.sleep(0.4)
        
        finally:
            if context:
                context.__exit__(None, None, None)
    
    async def _speak_once_async(self, text: str):
        """
        Async version for queue worker.
        """
        data, sr = await self._speak_chunk(text)
        self._play_audio_sync(data, sr)
        
    def speak(self, text: str):
        """
        Speak text.
        FAST PATH: Cached phrases play instantly.
        SLOW PATH: Uncached phrases go through queue.
        """
        if not text:
            return
        
        # FAST PATH: Check memory cache
        with self._cache_lock:
            if text in self.memory_cache:
                data, sr = self.memory_cache[text]
                # Play in separate thread (non-blocking, instant)
                threading.Thread(
                    target=self._play_audio_sync,
                    args=(data, sr),
                    daemon=True
                ).start()
                return
        
        # SLOW PATH: Queue for generation
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