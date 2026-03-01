"""
Streaming Text-to-Speech

Architecture:
1. Takes a SpeechPlan (list of tokens)
2. Retrieves cached AudioAtoms for each token
3. Concatenates with cross-fade for smooth prosody
4. Streams to audio output with low latency

Key Features:
- Start playback after first ~80-120ms buffered
- Cross-fade between atoms (10-30ms overlap)
- Interruptible playback
- Graceful handling of missing atoms
"""

import numpy as np
import threading
import queue
import time
import sounddevice as sd
from typing import Optional, List, Callable
from dataclasses import dataclass
from enum import Enum

from voice_output.atomic_cache import AtomicPhraseCache, AudioAtom
from voice_output.speech_planner import SpeechPlan, Verbosity
from utils.audio_state import AudioStateManager, AudioMode


class PlaybackState(Enum):
    """Current state of the streaming player."""
    IDLE = "idle"
    BUFFERING = "buffering"
    PLAYING = "playing"
    STOPPING = "stopping"


@dataclass
class StreamConfig:
    """Configuration for streaming playback."""
    sample_rate: int = 24000
    
    # Buffering
    min_buffer_ms: float = 100      # Start playback after this much buffered
    max_buffer_ms: float = 500      # Max buffer size
    
    # Cross-fade
    crossfade_ms: float = 20        # Overlap duration for cross-fade
    
    # Silence gaps
    inter_atom_silence_ms: float = 30   # Small gap between atoms
    
    @property
    def min_buffer_samples(self) -> int:
        return int(self.sample_rate * self.min_buffer_ms / 1000)
    
    @property
    def crossfade_samples(self) -> int:
        return int(self.sample_rate * self.crossfade_ms / 1000)
    
    @property
    def silence_samples(self) -> int:
        return int(self.sample_rate * self.inter_atom_silence_ms / 1000)


class StreamingTTS:
    """
    Streaming Text-to-Speech engine.
    
    Concatenates cached audio atoms with cross-fading
    and streams to audio output with minimal latency.
    """
    
    def __init__(
        self,
        cache: AtomicPhraseCache,
        config: Optional[StreamConfig] = None,
        audio_state: Optional[AudioStateManager] = None,
    ):
        """
        Args:
            cache: Pre-populated AtomicPhraseCache
            config: Streaming configuration
            audio_state: Shared audio state manager for coordination
        """
        self.cache = cache
        self.config = config or StreamConfig()
        self.audio_state = audio_state
        
        # Playback state
        self._state = PlaybackState.IDLE
        self._state_lock = threading.Lock()
        
        # Interrupt signal
        self._interrupt = threading.Event()
        
        # Current playback thread
        self._playback_thread: Optional[threading.Thread] = None
        
        # Queue for speech plans
        self._queue: queue.PriorityQueue = queue.PriorityQueue()
        
        # Worker thread
        self._shutdown = threading.Event()
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
    
    @property
    def state(self) -> PlaybackState:
        """Get current playback state."""
        with self._state_lock:
            return self._state
    
    def _set_state(self, state: PlaybackState):
        """Set playback state."""
        with self._state_lock:
            self._state = state
    
    def speak(self, plan: SpeechPlan, block: bool = False):
        """
        Speak a speech plan.
        
        Args:
            plan: SpeechPlan with tokens to speak
            block: If True, wait for playback to complete
        """
        if not plan.tokens:
            return
        
        # Add to queue with priority (negative because PriorityQueue is min-heap)
        self._queue.put((-plan.priority, time.time(), plan))
        
        if block:
            self._wait_for_idle()
    
    def speak_tokens(self, tokens: List[str], priority: int = 0, block: bool = False):
        """
        Convenience method to speak a list of tokens directly.
        
        Args:
            tokens: List of token strings
            priority: Priority level (higher = more important)
            block: If True, wait for playback to complete
        """
        plan = SpeechPlan(tokens=tokens, verbosity=Verbosity.NORMAL, priority=priority)
        self.speak(plan, block=block)
    
    def interrupt(self):
        """
        Interrupt current playback.
        
        Current speech stops, queue is NOT cleared.
        """
        self._interrupt.set()
        sd.stop()
    
    def clear_queue(self):
        """Clear all pending speech."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
    
    def stop(self):
        """Stop playback and clear queue."""
        self.interrupt()
        self.clear_queue()
    
    def _wait_for_idle(self, timeout: float = 10.0) -> bool:
        """Wait for playback to finish."""
        start = time.time()
        while time.time() - start < timeout:
            if self.state == PlaybackState.IDLE and self._queue.empty():
                return True
            time.sleep(0.05)
        return False
    
    def _worker_loop(self):
        """Background worker that processes the speech queue."""
        while not self._shutdown.is_set():
            try:
                # Get next plan (with timeout to check shutdown)
                try:
                    _, _, plan = self._queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                # Process this plan
                self._play_plan(plan)
                self._queue.task_done()
                
            except Exception as e:
                print(f"StreamingTTS worker error: {e}")
    
    def _play_plan(self, plan: SpeechPlan):
        """
        Play a single speech plan.
        
        This is where the magic happens:
        1. Retrieve atoms from cache
        2. Concatenate with cross-fade
        3. Stream to audio output
        """
        self._interrupt.clear()
        self._set_state(PlaybackState.BUFFERING)
        
        # Set audio state if available
        if self.audio_state:
            self.audio_state.set_mode(AudioMode.SPEAKING)
        
        try:
            # Collect audio atoms
            atoms: List[AudioAtom] = []
            for token in plan.tokens:
                atom = self.cache.get(token)
                if atom:
                    atoms.append(atom)
                else:
                    # Try to generate on-the-fly (fallback)
                    atom = self.cache.get_or_generate(token)
                    if atom:
                        atoms.append(atom)
                    else:
                        print(f"Warning: Missing atom for '{token}'")
            
            if not atoms:
                return
            
            # Concatenate atoms with cross-fade
            audio = self._concatenate_atoms(atoms)
            
            if len(audio) == 0:
                return
            
            # Play the concatenated audio
            self._set_state(PlaybackState.PLAYING)
            self._play_audio(audio)
            
        finally:
            self._set_state(PlaybackState.IDLE)
            if self.audio_state:
                self.audio_state.set_mode(AudioMode.IDLE)
    
    def _concatenate_atoms(self, atoms: List[AudioAtom]) -> np.ndarray:
        """
        Concatenate audio atoms with cross-fading.
        
        Cross-fade algorithm:
        1. For each pair of adjacent atoms
        2. Overlap last N samples of first with first N samples of second
        3. Apply linear fade-out to first, fade-in to second
        4. Sum the overlapped region
        
        Returns:
            Concatenated audio as float32 numpy array
        """
        if not atoms:
            return np.array([], dtype=np.float32)
        
        if len(atoms) == 1:
            return atoms[0].audio_data.copy()
        
        crossfade_samples = self.config.crossfade_samples
        silence_samples = self.config.silence_samples
        
        # Calculate total output length
        total_length = sum(len(atom.audio_data) for atom in atoms)
        # Subtract crossfade overlap for each junction
        total_length -= crossfade_samples * (len(atoms) - 1)
        # Add silence gaps
        total_length += silence_samples * (len(atoms) - 1)
        
        # Allocate output buffer
        output = np.zeros(total_length, dtype=np.float32)
        
        # Position in output buffer
        pos = 0
        
        for i, atom in enumerate(atoms):
            audio = atom.audio_data
            
            if i == 0:
                # First atom: just copy
                output[pos:pos + len(audio)] = audio
                pos += len(audio)
            else:
                # Subsequent atoms: cross-fade with previous
                
                # Add silence gap
                pos += silence_samples
                
                # Cross-fade region
                fade_len = min(crossfade_samples, len(audio), pos)
                
                if fade_len > 0:
                    # Create fade curves
                    fade_out = np.linspace(1.0, 0.0, fade_len, dtype=np.float32)
                    fade_in = np.linspace(0.0, 1.0, fade_len, dtype=np.float32)
                    
                    # Apply cross-fade
                    # Fade out the end of what's already in buffer
                    output[pos - fade_len:pos] *= fade_out
                    # Add faded-in start of new atom
                    output[pos - fade_len:pos] += audio[:fade_len] * fade_in
                    
                    # Copy rest of atom (after cross-fade region)
                    remaining = audio[fade_len:]
                    output[pos:pos + len(remaining)] = remaining
                    pos += len(remaining)
                else:
                    # No room for cross-fade, just append
                    output[pos:pos + len(audio)] = audio
                    pos += len(audio)
        
        # Trim to actual length used
        return output[:pos]
    
    def _play_audio(self, audio: np.ndarray):
        """
        Play audio with interrupt support.
        
        Uses sounddevice for playback.
        """
        if len(audio) == 0:
            return
        
        try:
            # Start playback
            sd.play(audio, self.config.sample_rate)
            
            # Wait for completion with interrupt checking
            while sd.get_stream().active:
                if self._interrupt.is_set():
                    sd.stop()
                    return
                time.sleep(0.01)  # 10ms poll interval
            
            # Small gap after playback
            time.sleep(0.1)
            
        except Exception as e:
            print(f"Playback error: {e}")
    
    def shutdown(self):
        """Shutdown the streaming TTS engine."""
        self._shutdown.set()
        self.stop()
        self._worker_thread.join(timeout=2.0)
    
    def is_speaking(self) -> bool:
        """Check if currently speaking."""
        return self.state in (PlaybackState.BUFFERING, PlaybackState.PLAYING)
    
    def get_queue_size(self) -> int:
        """Get number of pending speech plans."""
        return self._queue.qsize()


class StreamingTTSWithFallback(StreamingTTS):
    """
    Streaming TTS with fallback to full phrase generation.
    
    If atoms are missing, falls back to generating the full phrase
    using edge-tts directly.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fallback_enabled = True
    
    def _play_plan(self, plan: SpeechPlan):
        """
        Play plan with fallback for missing atoms.
        """
        # Check if all atoms are cached
        missing = [t for t in plan.tokens if not self.cache.is_cached(t)]
        
        if not missing:
            # All cached - use fast path
            super()._play_plan(plan)
        elif self._fallback_enabled and len(missing) == len(plan.tokens):
            # All missing - generate full phrase
            self._play_full_phrase(" ".join(plan.tokens))
        else:
            # Partial - try atom path with on-the-fly generation
            super()._play_plan(plan)
    
    def _play_full_phrase(self, text: str):
        """
        Fallback: generate and play full phrase.
        
        Used when atoms aren't available.
        """
        import asyncio
        import edge_tts
        import io
        
        self._set_state(PlaybackState.BUFFERING)
        
        if self.audio_state:
            self.audio_state.set_mode(AudioMode.SPEAKING)
        
        try:
            # Generate audio
            loop = asyncio.new_event_loop()
            try:
                async def generate():
                    communicate = edge_tts.Communicate(
                        text=text,
                        voice=self.cache.voice,
                        rate=self.cache.rate,
                        volume=self.cache.volume,
                    )
                    
                    audio_chunks = []
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            audio_chunks.append(chunk["data"])
                    
                    return b"".join(audio_chunks)
                
                audio_bytes = loop.run_until_complete(generate())
            finally:
                loop.close()
            
            if not audio_bytes:
                return
            
            # Decode
            audio_data, sr = self.cache._decode_mp3(audio_bytes)
            
            if sr != self.config.sample_rate:
                audio_data = self.cache._resample(audio_data, sr, self.config.sample_rate)
            
            # Normalize
            if len(audio_data) > 0:
                max_val = np.abs(audio_data).max()
                if max_val > 0:
                    audio_data = audio_data / max_val * 0.9
            
            # Play
            self._set_state(PlaybackState.PLAYING)
            self._play_audio(audio_data.astype(np.float32))
            
        finally:
            self._set_state(PlaybackState.IDLE)
            if self.audio_state:
                self.audio_state.set_mode(AudioMode.IDLE)


# Convenience function for integration
def create_streaming_tts(
    audio_state: Optional[AudioStateManager] = None,
    voice: str = "en-US-GuyNeural",
    rate: str = "+20%",
    cache_on_startup: bool = True,
    on_cache_progress: Optional[Callable] = None,
) -> StreamingTTSWithFallback:
    """
    Create a ready-to-use StreamingTTS instance.
    
    Args:
        audio_state: Shared audio state manager
        voice: TTS voice to use
        rate: Speech rate (e.g., "+20%")
        cache_on_startup: If True, start caching vocabulary immediately
        on_cache_progress: Optional callback(current, total, text) for caching progress
        
    Returns:
        Configured StreamingTTSWithFallback instance
    """
    # Create cache
    cache = AtomicPhraseCache(voice=voice, rate=rate)
    
    # Start caching vocabulary
    if cache_on_startup:
        cache.cache_vocabulary(on_progress=on_cache_progress)
    
    # Create streaming TTS
    config = StreamConfig(
        sample_rate=24000,
        min_buffer_ms=100,
        crossfade_ms=20,
        inter_atom_silence_ms=30,
    )
    
    tts = StreamingTTSWithFallback(
        cache=cache,
        config=config,
        audio_state=audio_state,
    )
    
    return tts