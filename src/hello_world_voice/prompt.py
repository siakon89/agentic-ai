"""Load Bob's RISEN system prompt."""

from pathlib import Path

_PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "bob.md"


def load_bob_prompt(*, use_audio: bool) -> str:
    """Read prompts/bob.md and append how this session hears and speaks."""
    prompt = _PROMPT_PATH.read_text(encoding="utf-8").strip()
    if use_audio:
        channel = (
            "Input is a live microphone. When you are allowed to speak, "
            "your voice is played on the speakers."
        )
    else:
        channel = (
            "Input is typed text. When you are allowed to speak, "
            "reply in text. There is no speaker."
        )
    return f"{prompt}\n\n# Channel\n{channel}\n"
