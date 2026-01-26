import asyncio
import threading
import queue
import edge_tts
import io
import sounddevice as sd
import soundfile as sf
from typing import Optional
from pathlib import Path
import hashlib
import numpy as np
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import IntEnum
import chess

from config import constants
from utils.audio_state import AudioStateManager, AudioContext, AudioMode
# TODO: Remove all prints for proper logging


class SpeechPriority(IntEnum):
    """Priority levels for speech queue (lower = higher priority)."""
    CRITICAL = 0    # "Check!", "Checkmate!", errors
    HIGH = 1        # Move announcements
    NORMAL = 2      # General feedback
    LOW = 3         # Verbose/optional announcements
    BACKGROUND = 4  # Pre-generation tasks


@dataclass(order=True)
class SpeechTask:
    """A task in the speech queue with priority."""
    priority: int
    text: str = field(compare=False)
    timestamp: float = field(default_factory=time.time, compare=False)
    

class TextToSpeech:
    def __init__(
        self,
        voice: str = "en-US-GuyNeural",
        rate: str = constants.TTS_RATE,
        volume: str = "+0%",
        cache_dir: Optional[str] = None,
        audio_state: Optional[AudioStateManager] = None
    ):
        self.voice = voice
        self.rate = rate
        self.volume = volume
        self.audio_state = audio_state

        # Optional disk cache for persistence across sessions
        if cache_dir:
            self.cache_dir = Path(cache_dir)
            self.cache_dir.mkdir(exist_ok=True)
        else:
            cache_dir = None
        
        # In-memory audio cache (phrase -> (audio_data, sample_rate))
        self.max_cache_size = constants.TTS_CACHE_SIZE
        self.memory_cache: dict[str, tuple[np.ndarray, int]] = {}
        self._cache_lock = threading.Lock()  
        
        # Standard sample rate for consistency
        self.target_sample_rate = 24000
        
        # Priority queue for speech tasks
        self._queue: queue.PriorityQueue[SpeechTask] = queue.PriorityQueue()
        self._shutdown = threading.Event()
        
        # Worker thread
        self._thread = threading.Thread(
            target=self._worker,
            daemon=True
        )
        self.thread.start()
        
        # Background pre-generation thread
        self._pregen_queue: queue.Queue[str] = queue.Queue()
        self._pregen_thread = threading.Thread(target=self._pregen_worker, daemon=True)
        self._pregen_thread.start()
        
        # Pre-cache common phrases on startup
        self._precache_common_phrases()
        
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text + voice settings."""
        key = f"{text}_{self.voice}_{self.rate}_{self.volume}"
        return hashlib.md5(key.encode()).hexdigest()
    
    def _add_to_cache(self, text: str, data: np.ndarray, sr: int):
        """Add audio to memory cache with LRU eviction."""
        with self._cache_lock:
            # Remove oldest if at capacity
            while len(self.memory_cache) >= self.max_cache_size:
                self.memory_cache.popitem(last=False)
            self.memory_cache[text] = (data, sr)
    
    def _get_from_cache(self, text: str) -> Optional[tuple[np.ndarray, int]]:
        """Get audio from cache, updating LRU order."""
        with self._cache_lock:
            if text in self.memory_cache:
                # Move to end (most recently used)
                self.memory_cache.move_to_end(text)
                return self.memory_cache[text]
        return None
    
    async def _generate_audio_async(self, text: str) -> tuple[np.ndarray, int]:
        """
        Generate audio using edge-tts directly to memory buffer.
        No disk I/O!
        """
        try: 
            communicate = edge_tts.Communicate(
                text=text,
                voice=self.voice,
                rate=self.rate,
                volume=self.volume,
            )
            
            # Collect audio chunks in memory
            audio_chunks = []
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_chunks.append(chunk["data"])
            
            if not audio_chunks:
                return (np.array([]), 0)
            
            # Combine chunks and decode
            audio_bytes = b"".join(audio_chunks)
            
            # edge_tts returns MP3, decode to numpy array
            audio_buffer = io.BytesIO(audio_bytes)
            
            # Use soundfile to read (requires audio data to be in WAV-like format)
            # since MP3, we need pydub or similar
            try:
                # Try direct read (works for some formats)
                data, sr = sf.read(audio_buffer, dtype="float32")
            except:
                # Fallback: use pydub for MP3 decoding
                try:
                    from pydub import AudioSegment
                    audio_buffer.seek(0)
                    audio_segment = AudioSegment.from_mp3(audio_buffer)
                    
                    # Convert to numpy array
                    samples = np.array(audio_segment.get_array_of_samples(), dtype=np.float32)
                    samples = samples / (2**15) # Normalize int16 to float
                    
                    # Handle stereo -> mono
                    if audio_segment.channels == 2:
                        samples = samples.reshape((-1, 2)).mean(axis=1)
                    
                    data = samples
                    sr = audio_segment.frame_rate
                except ImportError:
                    print("WARNING: pydub not installed, falling back to temp file")
                    return await self._generate_audio_via_file(text)        
            
            if sr != self.target_sample_rate:
                try:
                    import scipy.signal
                    num_samples = int(len(data) * self.target_sample_rate / sr) 
                    data = scipy.signal.resample(data, num_samples)
                    sr = self.target_sample_rate
                except ImportError:
                    pass # Use original sample rate
                
            # Normalize to prevent clipping
            if len(data) > 0:
                max_val = np.abs(data).max()
                if max_val > 0:
                    data = data / max_val * 0.95
                    
            return (data.astype(np.float32), sr)    
        
        except Exception as e:
            print(f"TTS generation error for '{text[:30]}...': {e}")
            return (np.array([]), 0)
    
    async def _generate_audio_via_file(self, text: str) -> tuple[np.ndarray, int]:
        """Fallback:"generate via temp file (slower but reliable)."""
        import tempfile
        import os
        
        try:
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
                tmp_path = tmp.name
                
                communicate = edge_tts.Communicate(
                    text=text,
                    voice=self.voice,
                    rate=self.rate,
                    volume=self.volume
                )
                await communicate.save(tmp_path)
                
                # Read and convert 
                from pydub import AudioSegment
                audio_segment = AudioSegment.from_mp3(tmp_path)
                
                samples = np.array(audio_segment.get_array_of_samples(), dtype=np.float32)
                samples = samples / (2**15)
                
                if audio_segment.channels == 2:
                    samples = samples.reshape((-1, 2)).mean(axis=1)
                    
                sr = audio_segment.frame_rate
                
                # Resample
                if sr != self.target_sample_rate:
                    import scipy.signal
                    num_samples = int(len(samples) * self.target_sample_rate / sr)
                    samples = scipy.signal.resample(samples, num_samples)
                    sr = self.target_sample_rate
                    
                # Normalize
                if len(samples) > 0:
                    max_val = np.abs(samples).max()
                    if max_val > 0:
                        samples = samples / max_val * 0.95
                
                return (samples.astype(np.float), sr)
            
        finally:
            try:
                os.unlink(tmp_path)
            except:
                pass
    
    def _get_or_generate_sync(self, text: str) -> tuple[np.ndarray, int]:
        """Synchronously get audio from cache or generate it."""
        # Check cache first
        cached = self._get_from_cache(text)
        if cached:
            return cached
        
        # Generate new audio
        loop = asyncio.new_event_loop()
        try:
            data, sr = loop.run_until_complete(self._generate_audio_async(text))
        finally:
            loop.close()
        
        # Cache it
        if len(data) > 0:
            self._add_to_cache(text, data, sr)
        
        return (data, sr)
    
    def _play_audio(self, data: np.ndarray, sr: int):
        """Play audio with proper state coordination."""
        if len(data) == 0:
            return
        
        context = AudioContext(self.audio_state, AudioMode.SPEAKING) if self.audio_state else None
        
        try:
            if context:
                context.__enter__()
                
            sd.play(data, sr)
            sd.wait()
            time.sleep(0.3) # Small gap after speech
        
        finally:
            if context:
                context.__exit__(None, None, None)
                
    def _worker(self):
        """Main worker thread processing the priority queue."""
        while not self._shutdown.is_set():
            try:
                # Get next task (blocks with timeout)
                try:
                    task = self._queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                # Get or generate audio
                data, sr = self._get_or_generate_sync(task.text)
                
                # Play it
                self._play_audio(data, sr)
                
                self._queue.task_done()
                
            except Exception as e:
                print(f"TTS worker error: {e}")
        
    def _pregen_worker(self):
        """Background worker for pre-generated likely phrases."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        while not self._shutdown.is_set():
            try: 
                # Get phrase to pre-generate (blocks with timeout)
                try:
                   text = self._pregen_queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                
                # Skip if already cached
                if self._get_from_cache(text):
                    self._pregen_queue.task_done()
                    continue
                    
                # Generate in background
                try:
                    data, sr = loop.run_until_complete(self._generate_audio_async(text))
                    if len(data) > 0: 
                        self._add_to_cache(text, data, sr)
                except Exception as e:
                    print(f"Pre-gen error for '{text[:20]}...': {e}")
                
                self._pregen_queue.task_done()
                
                # Small delay to not overwhelm edge-tts
                time.sleep(0.05)
                    
            except Exception as e:
                print(f"Pregen worker error: {e}")
        
        loop.close()
                    
    def speak(self, text: str, priority: SpeechPriority = SpeechPriority.NORMAL):
        """
        Speak text with priority queuing.
        
        Cached phrases play almost instantly.
        Uncached phrases are generated and queued.
        
        Args:
            text: Text to speak
            priority: Speech priority level
        """
        if not text:
            return
        
        # FAST PATH: If cached, play immediately in new thread
        cached = self._get_from_cache(text)
        if cached:
            data, sr = cached
            threading.Thread(
                target=self._play_audio,
                args=(data, sr),
                daemon=True
            ).start()
            return
        
        # SLOW PATH: Queue for generation
        task = SpeechTask(priority=priority, text=text)
        self._queue.put(task)
        
    def speak_critical(self, text: str):
        """Speak with critical priority (Check!, Checkmate!, errors)."""
        self.speak(text, SpeechPriority.CRITICAL)
    
    def speak_move(self, text: str):
        """Speak move announcement with high priority."""
        self.speak(text, SpeechPriority.HIGH)
    
    def pregenerate(self, phrases: list[str]):
        """
        Queue phrases for background pre-generation.
        
        Use this to warm the cache for likely upcoming phrases.
        """
        for phrase in phrases:
            if not self._get_from_cache(phrase):
                self._pregen_queue.put(phrase)
    
    def pregenerate_for_position(self, board: chess.Board, player_color: chess.Color):
        """
        Pre-generate likely announcements for current position.
        
        Analyzes legal moves and pre-generates audio for likely outcomes.
        """
        phrases_to_generate = []
        
        # Pre-generate for opponent's likely responses
        opponent_color = not player_color
        color_name = "Black" if opponent_color == chess.BLACK else "White"
        
        # Get opponent's legal moves (if it were their turn)
        # We'll generate for common piece movements

        for move in list(board.legal_moves)[:10]:  # Top 10 moves
            piece = board.piece_at(move.from_square)
            if piece:
                piece_name = self._piece_name(piece.piece_type)
                dest = chess.square_name(move.to_square)
                
                # Capture?
                is_capture = board.is_capture(move)
                
                if is_capture:
                    phrase = f"{piece_name} takes {dest}"
                else:
                    phrase = f"{piece_name} to {dest}"
                
                # Full announcement
                full_phrase = f"{color_name} {phrase.lower()}"
                phrases_to_generate.append(full_phrase)
        
        # Also pre-generate "Check!" since it's common
        phrases_to_generate.append("Check!")
        
        self.pregenerate(phrases_to_generate)
    
    def _piece_name(self, piece_type: int) -> str:
        """Get piece name from chess piece type."""
        names = {
            chess.PAWN: "Pawn",
            chess.KNIGHT: "Knight",
            chess.BISHOP: "Bishop",
            chess.ROOK: "Rook",
            chess.QUEEN: "Queen",
            chess.KING: "King",
        }
        return names.get(piece_type, "Piece")

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
        
        # Queue for background generation
        self.pregenerate(common_phrases)

    def shutdown(self):
        """Clean shutdown of all threads."""
        self._shutdown.set()
        
        # Clear queues
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except:
                pass
        
        while not self._pregen_queue.empty():
            try:
                self._pregen_queue.get_nowait()
            except:
                pass
        
        # Wait for threads
        self._thread.join(timeout=2)
        self._pregen_thread.join(timeout=2)
        
    def get_cache_stats(self) -> dict:
        """
        Get statistics about the cache.
        Useful for debugging and optimization.
        """
        with self._cache_lock:
            cache_count = len(self.memory_cache)
            
            # Estimate memory usage
            total_samples = sum(
                len(data) for data, _ in self.memory_cache.values()
            )
            memory_mb = (total_samples * 4) / (1024 * 1024) # float32 = 4 bytes
            
        return {
            "cached_phrases": cache_count,
            "max_cache_size": self.max_cache_size,
            "estimated_memory_mb": round(memory_mb, 2),
            "queue_size": self._queue.qsize(),
            "pregen_queue_size": self._pregen_queue.qsize(),
        }
        
    def clear_cache(self):
        """Clear the memory cache."""
        with self._cache_lock:
            self.memory_cache.clear()