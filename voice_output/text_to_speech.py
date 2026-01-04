import asyncio
import threading
import queue
import edge_tts
import tempfile
import os
import sounddevice as sd
import soundfile as sf


class TextToSpeech:
    def __init__(
        self,
        voice: str = "en-US-AriaNeural",
        rate: str = "+0%",
        volume: str = "+0%"
    ):
        self.voice = voice
        self.rate = rate
        self.volume = volume

        self.queue: queue.Queue[str | None] = queue.Queue()
        self.thread = threading.Thread(
            target=self._worker,
            daemon=True
        )
        self.thread.start()

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
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            path = f.name

        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=self.voice,
                rate=self.rate,
                volume=self.volume,
            )
            await communicate.save(path)

            data, samplerate = sf.read(path, dtype="float32")
            sd.play(data, samplerate)
            sd.wait()

        finally:
            if os.path.exists(path):
                os.remove(path)

    def speak(self, text: str):
        if text:
            self.queue.put(text)

    def shutdown(self):
        self.queue.put(None)
