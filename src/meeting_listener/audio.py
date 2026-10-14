"""Microphone and speaker setup for the listening session."""

import os
from contextlib import contextmanager
from typing import Any

from strands.bidi.io import AudioIO, ConsoleIO
from strands.bidi.types.io import InputStream, OutputStream

_MISSING_DEVICE = -9996
_PLACEHOLDER = "Listening. Say 'Ultron, summarize' for notes…"


def default_audio_devices_present(audio: Any) -> bool:
    """Return whether PortAudio can open a default microphone and speaker."""
    try:
        audio.get_default_input_device_info()
        audio.get_default_output_device_info()
    except OSError:
        return False
    return True


def audio_devices_available() -> bool:
    """Probe the sound devices, hiding PortAudio's missing-card messages."""
    import pyaudio

    with _silenced_stderr():
        audio = pyaudio.PyAudio()
        try:
            return default_audio_devices_present(audio)
        finally:
            audio.terminate()


def is_missing_audio_device(error: OSError) -> bool:
    return error.errno == _MISSING_DEVICE or "device" in str(error).lower()


def open_streams(use_audio: bool) -> tuple[list[InputStream], list[OutputStream]]:
    """Return keyboard input, and the microphone plus speakers when audio exists."""
    console = ConsoleIO(placeholder=_PLACEHOLDER, show_reasoning=False)
    if not use_audio:
        return [console.input()], [console.output()]

    audio = AudioIO(console=console, audio_processor=True)
    return [console.input(), audio.input()], [audio.output()]


@contextmanager
def _silenced_stderr():
    saved = os.dup(2)
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, 2)
    try:
        yield
    finally:
        os.dup2(saved, 2)
        os.close(saved)
        os.close(devnull)
