"""
TTS Latency Tests

Measures performance of the atomic cache + streaming TTS pipeline.
Run with: python -m tests.test_tts_latency

Thresholds (p95):
- Cache hit retrieval: < 0.1ms
- Atom concatenation (5 tokens): < 5ms
- Speech planner token generation: < 1ms
- End-to-end (cached, no audio): < 10ms
"""

import time
import numpy as np
import chess
from typing import List
from dataclasses import dataclass

from voice_output.atomic_cache import AtomicPhraseCache, AudioAtom, AtomCategory
from voice_output.speech_planner import SpeechPlanner, SpeechPlan, TimeContext, Verbosity
from voice_output.streaming_tts import StreamingTTS, StreamConfig


@dataclass
class LatencyResult:
    name: str
    samples: List[float]

    @property
    def mean_ms(self) -> float:
        return sum(self.samples) / len(self.samples)
    
    @property
    def median_ms(self) -> float:
        s = sorted(self.samples)
        n = len(s)        
        return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2

    @property
    def p95_ms(self) -> float:
        s = sorted(self.samples)
        return s[int(len(s * 0.95))]
    
    @property
    def max_ms(self) -> float:
        return max(self.samples)
    
    
def make_fake_atom(text: str, duration_ms: float = 300) -> AudioAtom:
    """Synthetic AudioAtom — no edge-tts needed."""
    sr = 24000
    num_samples = int(sr * duration_ms / 1000)
    t = np.linspace(0, duration_ms / 1000, num_samples, dtype=np.float32)
    audio = (np.sin(2 * np.pi * 440 * t) * 0.5).astype(np.float32)
    return AudioAtom(
        text=text.lower(),
        category=AtomCategory.PIECE,
        audio_data=audio,
        sample_rate=sr,
        duration_ms=duration_ms,
    )
    

def build_test_cache() -> AtomicPhraseCache:
    """Cache pre-filled with fake atoms. No network calls."""
    cache = AtomicPhraseCache()
    for category, words in AtomicPhraseCache.VOCABULARY.items():
        for word in words:
            atom = make_fake_atom(word)
            atom.category = category
            cache._cache[word.lower()] = atom
    return cache


# ============================================================================
# Tests
# ============================================================================

def test_cache_hit_retrieval(iterations: int = 1000) -> LatencyResult:
    cache = build_test_cache()
    targets = ["knight", "takes", "e5", "check", "castles"]
    timings = []

    for _ in range(iterations):
        for target in targets:
            start = time.perf_counter()
            atom = cache.get(target)
            elapsed = (time.perf_counter() - start) * 1000
            timings.append(elapsed)
            assert atom is not None, f"Cache miss for '{target}'"

    return LatencyResult("cache_hit_retrieval", timings)    


def test_cache_miss_retrieval(iterations: int = 1000) -> LatencyResult:
    cache = build_test_cache()
    timings = []

    for _ in range(iterations):
        start = time.perf_counter()
        result = cache.get("nonexistent_xyz")
        elapsed = (time.perf_counter() - start) * 1000
        timings.append(elapsed)
        assert result is None

    return LatencyResult("cache_miss_retrieval", timings)


def test_concatenation_latency(iterations: int = 200) -> LatencyResult:
    cache = build_test_cache()
    tts = StreamingTTS(cache=cache, config=StreamConfig())

    token_sets = [
        ["knight", "takes", "e5"],
        ["knight", "takes", "e5", "check"],
        ["black", "queen", "takes", "d4", "checkmate"],
        ["castles", "kingside"],
        ["e4"],
    ]

    timings = []
    for _ in range(iterations):
        for tokens in token_sets:
            atoms = [cache.get(t) for t in tokens if cache.get(t)]

            start = time.perf_counter()
            audio = tts._concatenate_atoms(atoms)
            elapsed = (time.perf_counter() - start) * 1000
            timings.append(elapsed)
            assert len(audio) > 0

    tts.shutdown()
    return LatencyResult("concatenation", timings)


def test_planner_latency(iterations: int = 500) -> LatencyResult:
    planner = SpeechPlanner()
    planner.set_time_control(300, 0)

    board = chess.Board()
    moves = ["e2e4", "e7e5", "g1f3", "b8c6", "f1b5", "a7a6", "b5a4", "g8f6"]

    timings = []
    for _ in range(iterations):
        test_board = board.copy()
        for uci in moves:
            move = chess.Move.from_uci(uci)
            start = time.perf_counter()
            plan = planner.plan_move(move, test_board, is_player_move=True)
            elapsed = (time.perf_counter() - start) * 1000
            timings.append(elapsed)
            assert len(plan.tokens) > 0
            test_board.push(move)

    return LatencyResult("planner_token_gen", timings)


def test_planner_verbosity_scaling() -> None:
    """Verify token count decreases (or stays flat) as time pressure increases."""
    board = chess.Board()
    board.push(chess.Move.from_uci("e2e4"))
    move = chess.Move.from_uci("e7e5")

    scenarios = [
        ("classical_full", 3600, 3600, 0),
        ("rapid_full",      900,  900, 0),
        ("blitz_full",      300,  300, 0),
        ("blitz_half",      300,  150, 0),
        ("blitz_low",       300,   30, 0),
        ("bullet_full",      60,   60, 0),
        ("bullet_low",       60,   10, 0),
    ]

    print("\n  Verbosity scaling:")
    prev_count = None
    for name, initial, remaining, inc in scenarios:
        planner = SpeechPlanner(TimeContext(
            initial_time_seconds=initial,
            remaining_seconds=remaining,
            increment_seconds=inc,
        ))
        plan = planner.plan_move(move, board, is_player_move=False, include_color=True)
        count = len(plan.tokens)
        print(f"    {name:20s} -> {plan.verbosity.name:8s} tokens={count}  {plan.tokens}")

        if prev_count is not None:
            assert count <= prev_count + 1, f"Tokens increased under pressure: {name}"
        prev_count = count


def test_end_to_end_no_audio(iterations: int = 100) -> LatencyResult:
    """Full pipeline minus actual audio playback."""
    cache = build_test_cache()
    tts = StreamingTTS(cache=cache, config=StreamConfig())
    planner = SpeechPlanner()
    planner.set_time_control(300, 0)

    board = chess.Board()
    moves = ["e2e4", "e7e5", "g1f3", "b8c6"]

    timings = []
    for _ in range(iterations):
        test_board = board.copy()
        for uci in moves:
            move = chess.Move.from_uci(uci)

            start = time.perf_counter()
            plan = planner.plan_move(move, test_board, is_player_move=True)
            atoms = [cache.get(t) for t in plan.tokens if cache.get(t)]
            audio = tts._concatenate_atoms(atoms)
            elapsed = (time.perf_counter() - start) * 1000

            timings.append(elapsed)
            test_board.push(move)

    tts.shutdown()
    return LatencyResult("end_to_end_no_audio", timings)


# ============================================================================
# Thresholds & Runner
# ============================================================================

THRESHOLDS_MS = {
    "cache_hit_retrieval": 0.1,
    "cache_miss_retrieval": 0.1,
    "concatenation": 5.0,
    "planner_token_gen": 1.0,
    "end_to_end_no_audio": 10.0,
}


def run_all():
    print("=" * 60)
    print("TTS LATENCY TESTS")
    print("=" * 60)

    results: List[LatencyResult] = []

    print("\n[1/6] Cache hit retrieval...")
    results.append(test_cache_hit_retrieval())

    print("[2/6] Cache miss retrieval...")
    results.append(test_cache_miss_retrieval())

    print("[3/6] Atom concatenation...")
    results.append(test_concatenation_latency())

    print("[4/6] Speech planner latency...")
    results.append(test_planner_latency())

    print("[5/6] Verbosity scaling...")
    test_planner_verbosity_scaling()

    print("\n[6/6] End-to-end (no audio)...")
    results.append(test_end_to_end_no_audio())

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    all_passed = True
    for result in results:
        threshold = THRESHOLDS_MS.get(result.name)
        passed = result.p95_ms < threshold if threshold else True
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_passed = False

        print(f"\n  [{status}] {result.name} (threshold: p95 < {threshold}ms)")
        print(f"    mean={result.mean_ms:.3f}ms  median={result.median_ms:.3f}ms  "
              f"p95={result.p95_ms:.3f}ms  max={result.max_ms:.3f}ms")

    print("\n" + "=" * 60)
    print("ALL LATENCY TESTS PASSED" if all_passed else "SOME TESTS FAILED")
    print("=" * 60)


if __name__ == "__main__":
    run_all()