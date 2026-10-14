"""Turn BidiAgent history into a readable transcript."""

from collections.abc import Iterable, Mapping
from typing import Any

_UNAVAILABLE = "[Transcript unavailable.]"
_SESSION_CUE = "The listening session is open."
_SPEAKER = {"user": "Speaker", "assistant": "Ultron"}


def format_transcript(messages: Iterable[Mapping[str, Any]]) -> str:
    """Join completed speech and text turns, skipping tool traffic.

    Microphone audio is stored as user text. The listener's own replies are
    assistant text. Tool calls are omitted because they are session control,
    not part of the conversation being summarized.
    """
    lines = [_line(message) for message in messages]
    return "\n".join(line for line in lines if line)


def _line(message: Mapping[str, Any]) -> str:
    text = _message_text(message.get("content", []))
    if not text or text.startswith(_SESSION_CUE):
        return ""
    role = str(message.get("role", "user"))
    speaker = _SPEAKER.get(role, role)
    return f"{speaker}: {text}"


def _message_text(content: object) -> str:
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for block in content:
        text = _block_text(block)
        if text:
            parts.append(text)
    return " ".join(parts)


def _block_text(block: object) -> str:
    if isinstance(block, Mapping):
        value = block.get("text")
    else:
        value = getattr(block, "text", None)
    if not isinstance(value, str):
        return ""
    text = " ".join(value.split())
    if not text or text == _UNAVAILABLE:
        return ""
    return text
