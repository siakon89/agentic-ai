"""Turn BidiAgent history into a readable transcript."""

from collections.abc import Iterable, Mapping
from typing import Any

_UNAVAILABLE = "[Transcript unavailable.]"
_SESSION_CUE = "The listening session is open."


def format_transcript(
    messages: Iterable[Mapping[str, Any]],
    *,
    assistant_name: str = "Ultron",
) -> str:
    """Join completed speech and text turns, skipping tool traffic.

    Microphone audio is stored as user text. The agent's own replies are
    assistant text. Tool calls are omitted because they are session control,
    not part of the conversation being recorded.
    """
    lines = [_line(message, assistant_name) for message in messages]
    return "\n".join(line for line in lines if line)


def _line(message: Mapping[str, Any], assistant_name: str) -> str:
    text = _message_text(message.get("content", []))
    if not text or text.startswith(_SESSION_CUE):
        return ""
    role = str(message.get("role", "user"))
    speaker = "Speaker" if role == "user" else assistant_name
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
