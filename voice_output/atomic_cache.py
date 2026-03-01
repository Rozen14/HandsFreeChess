"""
Atomic Phrase Cache

Caches small, reusable speech atoms that can be concatenated:
- Pieces: "knight", "bishop", "rook", "queen", "king", "pawn"
- Verbs: "to", "takes", "captures"
- Squares: "a1" through "h8"
- Suffixes: "check", "checkmate"
- Specials: "castles kingside", "castles queenside", "en passant"
- Promotions: "promotes to queen", "to queen"

Design principle: Cache atoms, concatenate at runtime, cross-fade for smooth playback.
"""


import numpy as np
import threading
import asyncio
from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple
from enum import Enum
import io

# Will use edge_tts for generation
import edge_tts


class AtomCategory(Enum):
    """Categories of speech atoms."""
    PIECE = "piece"
    VERB = "verb"
    SQUARE = "square"
    FILE = "file"
    RANK = "rank"
    SUFFIX = "suffix"
    SPECIAL = "special"
    COLOR = "color"
    STATUS = "status"
    ERROR = "error"


@dataclass
class AudioAtom:
    """A cached audio atom."""
    text: str
    category: AtomCategory
    audio_data: np.ndarray  # float32, mono
    sample_rate: int
    duration_ms: float
    
    @property
    def duration_samples(self) -> int:
        return len(self.audio_data)
    

class AtomicPhraseCache:
    """
    Manages a cache of small, reusable speech atoms.
    
    Philosophy:
    - Cache small atoms (< 500ms each)
    - Concatenate at runtime for any phrase
    - Cross-fade between atoms for smooth prosody
    """
    # Standard chess vocabulary
    VOCABULARY = {
        AtomCategory.PIECE: [
            "pawn", "knight", "bishop", "rook", "queen", "king"
        ],
        AtomCategory.VERB: [
            "to", "takes", "promotes to"
        ],
        AtomCategory.SQUARE: [
            f"{file}{rank}" 
            for file in "abcdefgh" 
            for rank in "12345678"
        ],
        AtomCategory.SUFFIX: [
            "check", "checkmate", "stalemate",
        ],
        AtomCategory.SPECIAL: [
            "castles kingside", "castles queenside", 
            "en passant",
        ],
        AtomCategory.COLOR: [
            "white", "black",
        ],
        AtomCategory.STATUS: [
            "game started", "you are white", "make your move",
            "waiting for opponent", "timed out", "nothing to repeat",
            "game over", "which side",
        ],
        AtomCategory.ERROR: [
            "illegal", "not legal", "ambiguous",
            "repeat", "didn't catch that",
            "please repeat", "castling is not legal",
        ],
    }
    
    def __init__(
        self,
        voice: str = "en-US-GuyNeural",
        rate: str = "+20%",  # Slightly faster for atoms
        volume: str = "+0%",
        target_sample_rate: int = 24000,
    ):
        self.voice = voice
        self.rate = rate
        self.volume = volume
        self.target_sample_rate = target_sample_rate
        
        # Cache: text -> AudioAtom
        self._cache: Dict[str, AudioAtom] = {}
        self._cache_lock = threading.Lock()
        
        # Generation state
        self._generating = False
        self._generation_complete = threading.Event()
        
    def get(self, text: str) -> Optional[AudioAtom]:
        """
        Get a cached atom by text.
        
        Args:
            text: The atom text (e.g., "knight", "e4", "takes")
            
        Returns:
            AudioAtom if cached, None otherwise
        """
        text_lower = text.lower().strip()
        with self._cache_lock:
            return self._cache.get(text_lower)
        
    def get_or_generate(self, text: str, category: AtomCategory = AtomCategory.PIECE) -> Optional[AudioAtom]:
        """
        Get atom from cache, or generate synchronously if missing.
        
        For runtime use when an atom is unexpectedly missing.
        """
        atom = self.get(text)
        if atom:
            return atom
        
        # Generate synchronously (blocking)
        loop = asyncio.new_event_loop()
        try:
            audio_data, sr = loop.run_until_complete(self._generate_audio(text))
            if len(audio_data) > 0:
                atom = AudioAtom(
                    text=text.lower(),
                    category=category,
                    audio_data=audio_data,
                    sample_rate=sr,
                    duration_ms=(len(audio_data) / sr) * 1000
                )
                with self._cache_lock:
                    self._cache[text.lower()] = atom
                return atom
        finally:
            loop.close()
        
        return None
    
    def is_cached(self, text: str) -> bool:
        """Check if an atom is cached."""
        return self.get(text) is not None
    
    def cache_vocabulary(self, on_progress: Optional[callable] = None):
        """
        Cache all vocabulary atoms in background.
        
        Args:
            on_progress: Optional callback(current, total, text) for progress updates
        """
        def _generate_all():
            self._generating = True
            self._generation_complete.clear()
            
            # Collect all atoms to generate
            all_atoms: List[Tuple[str, AtomCategory]] = []
            for category, words in self.VOCABULARY.items():
                for word in words:
                    all_atoms.append((word, category))
            
            total = len(all_atoms)
            
            # Create event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                for i, (text, category) in enumerate(all_atoms):
                    # Skip if already cached
                    if self.is_cached(text):
                        if on_progress:
                            on_progress(i + 1, total, text)
                        continue
                    
                    # Generate audio
                    try:
                        audio_data, sr = loop.run_until_complete(self._generate_audio(text))
                        
                        if len(audio_data) > 0:
                            atom = AudioAtom(
                                text=text.lower(),
                                category=category,
                                audio_data=audio_data,
                                sample_rate=sr,
                                duration_ms=(len(audio_data) / sr) * 1000
                            )
                            
                            with self._cache_lock:
                                self._cache[text.lower()] = atom
                    
                    except Exception as e:
                        print(f"Failed to cache '{text}': {e}")
                    
                    if on_progress:
                        on_progress(i + 1, total, text)
                
            finally:
                loop.close()
                self._generating = False
                self._generation_complete.set()
        
        thread = threading.Thread(target=_generate_all, daemon=True)
        thread.start()
        return thread
    
    def wait_for_cache_ready(self, timeout: Optional[float] = None) -> bool:
        """
        Block until vocabulary caching is complete.
        
        Args:
            timeout: Max seconds to wait (None = forever)
            
        Returns:
            True if ready, False if timeout
        """
        return self._generation_complete.wait(timeout=timeout)
    
    async def _generate_audio(self, text: str) -> Tuple[np.ndarray, int]:
        """
        Generate audio for a single atom using edge-tts.
        
        Returns:
            Tuple of (audio_data as float32 numpy array, sample_rate)
        """
        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=self.voice,
                rate=self.rate,
                volume=self.volume,
            )
            
            # Collect audio chunks
            audio_chunks = []
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_chunks.append(chunk["data"])
            
            if not audio_chunks:
                return (np.array([], dtype=np.float32), self.target_sample_rate)
            
            # Combine chunks
            audio_bytes = b"".join(audio_chunks)
            
            # Decode MP3 to numpy
            audio_data, sr = self._decode_mp3(audio_bytes)
            
            # Resample if needed
            if sr != self.target_sample_rate:
                audio_data = self._resample(audio_data, sr, self.target_sample_rate)
                sr = self.target_sample_rate
            
            # Normalize
            if len(audio_data) > 0:
                max_val = np.abs(audio_data).max()
                if max_val > 0:
                    audio_data = audio_data / max_val * 0.9
            
            return (audio_data.astype(np.float32), sr)
            
        except Exception as e:
            print(f"Audio generation error for '{text}': {e}")
            return (np.array([], dtype=np.float32), self.target_sample_rate)
        
    def _decode_mp3(self, mp3_bytes: bytes) -> Tuple[np.ndarray, int]:
        """Decode MP3 bytes to numpy array."""
        try:
            from pydub import AudioSegment
            
            audio_buffer = io.BytesIO(mp3_bytes)
            audio_segment = AudioSegment.from_mp3(audio_buffer)
            
            # Convert to numpy
            samples = np.array(audio_segment.get_array_of_samples(), dtype=np.float32)
            samples = samples / (2**15)  # Normalize int16 to float
            
            # Stereo to mono
            if audio_segment.channels == 2:
                samples = samples.reshape((-1, 2)).mean(axis=1)
            
            return (samples, audio_segment.frame_rate)
            
        except ImportError:
            raise ImportError("pydub is required for MP3 decoding: pip install pydub")
        
    def _resample(self, audio: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
        """Resample audio to target sample rate."""
        if src_rate == dst_rate:
            return audio
        
        try:
            import scipy.signal
            num_samples = int(len(audio) * dst_rate / src_rate)
            return scipy.signal.resample(audio, num_samples)
        except ImportError:
            # Fallback: simple linear interpolation
            ratio = dst_rate / src_rate
            indices = np.arange(0, len(audio), 1/ratio)
            indices = indices[indices < len(audio) - 1].astype(int)
            return audio[indices]
        
    def get_stats(self) -> dict:
        """Get cache statistics."""
        with self._cache_lock:
            total_duration = sum(atom.duration_ms for atom in self._cache.values())
            total_samples = sum(len(atom.audio_data) for atom in self._cache.values())
            memory_mb = (total_samples * 4) / (1024 * 1024)  # float32 = 4 bytes
            
            return {
                "cached_atoms": len(self._cache),
                "total_duration_ms": round(total_duration, 1),
                "memory_mb": round(memory_mb, 2),
                "generating": self._generating,
            }
    
    def get_atoms_for_phrase(self, tokens: List[str]) -> List[Optional[AudioAtom]]:
        """
        Get cached atoms for a list of tokens.
        
        Args:
            tokens: List of text tokens (e.g., ["knight", "takes", "e5"])
            
        Returns:
            List of AudioAtom (or None for missing atoms)
        """
        return [self.get(token) for token in tokens]