"""Microphone and speaker setup for the listening session."""

import ctypes
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from strands.bidi.io import AudioIO, ConsoleIO
from strands.bidi.types.io import InputStream, OutputStream

_MISSING_DEVICE = -9996
_PLACEHOLDER = "Listening. Say 'Bob' to talk, or 'Bob, take notes'…"
_WSL_PLAYBACK_LATENCY_MS = 120
_alsa_error_handler: object | None = None


def default_audio_devices_present(audio: Any) -> bool:
    """Return whether PortAudio can open a default microphone and speaker."""
    try:
        audio.get_default_input_device_info()
        audio.get_default_output_device_info()
    except OSError:
        return False
    return True


def playback_latency_ms() -> int | None:
    """Return the speaker buffer depth, in milliseconds.

    WSL's default buffer is shorter than the gap between audio callbacks, so ALSA
    reports an underrun and recovers. A deeper Pulse buffer covers that gap.
    ``PULSE_LATENCY_MSEC`` overrides the depth.
    """
    _ignore_recovered_underruns()
    raw = os.environ.get("PULSE_LATENCY_MSEC", "").strip()
    if raw.isdigit():
        return min(int(raw), 1000)
    if not _on_wsl():
        return None
    os.environ["PULSE_LATENCY_MSEC"] = str(_WSL_PLAYBACK_LATENCY_MS)
    return _WSL_PLAYBACK_LATENCY_MS


def audio_devices_available() -> bool:
    """Probe the sound devices, hiding PortAudio's missing-card messages."""
    playback_latency_ms()
    import pyaudio

    with _silenced_stderr():
        audio = pyaudio.PyAudio()
        try:
            return default_audio_devices_present(audio)
        finally:
            audio.terminate()


def is_missing_audio_device(error: OSError) -> bool:
    return error.errno == _MISSING_DEVICE or "device" in str(error).lower()


def open_streams(
    use_audio: bool,
    *,
    placeholder: str = _PLACEHOLDER,
    show_text: bool = True,
) -> tuple[list[InputStream], list[OutputStream]]:
    """Return keyboard input, and the microphone plus speakers when audio exists."""
    console = ConsoleIO(placeholder=placeholder, show_reasoning=False, show_text=show_text)
    if not use_audio:
        return [console.input()], [console.output()]

    latency_ms = playback_latency_ms()
    processor: bool | dict[str, int | bool] = True
    if latency_ms:
        processor = {"echo_cancellation": True, "stream_delay_ms": latency_ms}
    audio = AudioIO(console=console, audio_processor=processor)
    return [console.input(), audio.input()], [audio.output()]


def _on_wsl() -> bool:
    try:
        release = Path("/proc/version").read_text(encoding="utf-8").lower()
    except OSError:
        return False
    return "microsoft" in release or "wsl" in release


def _is_recovered_underrun(function: bytes | None, fmt: bytes | None) -> bool:
    """ALSA already restarted the stream. The line is not a failed session."""
    name = function.decode(errors="replace") if function else ""
    text = fmt.decode(errors="replace") if fmt else ""
    return name == "snd_pcm_recover" and "underrun" in text.lower()


def _ignore_recovered_underruns() -> None:
    """Drop ALSA's recovered-underrun notice and keep every other ALSA error."""
    global _alsa_error_handler
    if _alsa_error_handler is not None:
        return
    try:
        asound = ctypes.CDLL("libasound.so.2")
    except OSError:
        _alsa_error_handler = False
        return

    handler_type = ctypes.CFUNCTYPE(
        None, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p
    )

    def _on_alsa_error(
        _filename: bytes | None,
        _line: int,
        function: bytes | None,
        _err: int,
        fmt: bytes | None,
    ) -> None:
        if _is_recovered_underrun(function, fmt):
            return
        name = function.decode(errors="replace") if function else "alsa"
        text = fmt.decode(errors="replace") if fmt else ""
        sys.stderr.write(f"ALSA lib {name}: {text}\n")

    _alsa_error_handler = handler_type(_on_alsa_error)
    asound.snd_lib_error_set_handler(_alsa_error_handler)


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
