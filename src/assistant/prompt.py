"""Load Assistant's RISEN system prompt and the registered capabilities."""

from pathlib import Path

from assistant.capabilities import instructions

_PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "assistant.md"


def load_assistant_prompt(*, use_audio: bool) -> str:
    """Read prompts/assistant.md and append each capability, then the audio channel."""
    prompt = _PROMPT_PATH.read_text(encoding="utf-8").strip()
    capability_text = instructions().strip()
    if use_audio:
        channel = (
            "Input is a live microphone. When you are allowed to speak, "
            "answer with spoken audio on the speakers. Do not answer in writing."
        )
    else:
        channel = "Input is typed text. When you are allowed to speak, reply in text."
    return f"{prompt}\n\n{capability_text}\n\n# Channel\n{channel}\n"
