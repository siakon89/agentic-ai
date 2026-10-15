"""Capabilities Bob can call during a session.

Add a swarm by creating a package next to ``research`` and appending an
instance to ``CAPABILITIES``. Each capability supplies its tools and the
instructions Bob needs to decide when to call them.
"""

from collections.abc import Sequence
from typing import Protocol

from strands.types.tools import AgentTool

from assistant.capabilities.research import Research


class Capability(Protocol):
    """One ability Bob can use without ending the session."""

    def tools(self) -> Sequence[AgentTool]:
        """Tools to register on the voice agent."""

    def instructions(self) -> str:
        """Prompt text that tells Bob when to call those tools."""


CAPABILITIES: list[Capability] = [Research()]


def tools() -> list[AgentTool]:
    """Every tool from the registered capabilities."""
    registered: list[AgentTool] = []
    for capability in CAPABILITIES:
        registered.extend(capability.tools())
    return registered


def instructions() -> str:
    """Prompt sections for the registered capabilities."""
    sections = [capability.instructions().strip() for capability in CAPABILITIES]
    return "\n\n".join(section for section in sections if section)
