import os


def setup_ffmpeg():
    """Add ffmpeg to system PATH."""
    ffmpeg_path = r"C:\ffmpeg\ffmpeg-8.0.1-essentials_build\bin"
    os.environ["PATH"] += os.pathsep + ffmpeg_path