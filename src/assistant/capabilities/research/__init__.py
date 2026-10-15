"""Web research swarm: search, check, write, then read or email the report."""

from pathlib import Path

from strands.types.tools import AgentTool

from assistant.capabilities.research.tools import deep_research, email_research, read_research

_INSTRUCTIONS = Path(__file__).parent / "prompts" / "instructions.md"


class Research:
    """Research a topic, then read or email the saved report."""

    def tools(self) -> list[AgentTool]:
        return [deep_research, read_research, email_research]

    def instructions(self) -> str:
        return _INSTRUCTIONS.read_text(encoding="utf-8")
