"""Three agents that research a topic on the public web, in a fixed order."""

from dataclasses import dataclass
from pathlib import Path

from strands import Agent
from strands.models import BedrockModel
from strands.multiagent import GraphBuilder
from strands.multiagent.base import MultiAgentResult, Status
from strands.multiagent.graph import Graph
from strands.vended_tools import web_fetch

from assistant.capabilities.research.search import NOVA_2_LITE, web_search
from hello_world_voice.config import aws_region

_PROMPTS = Path(__file__).parent / "prompts"


@dataclass(frozen=True)
class ResearchReport:
    """The gatherer's short brief and sources list."""

    short: str
    long: str
    full: str


def run_research(topic: str) -> ResearchReport:
    """Run researcher, reviewer, and gatherer, then return both lengths."""
    graph = build_research_swarm()
    result = graph(
        "Research this topic on the public web. "
        "The researcher searches once, the reviewer checks the claims from that packet, "
        "and the gatherer writes the short brief and the sources list.\n\n"
        f"Topic: {topic}"
    )
    if result.status is not Status.COMPLETED or "gatherer" not in result.results:
        raise RuntimeError(_failure_reason(result))
    return split_report(str(result.results["gatherer"]))


def build_research_swarm() -> Graph:
    """Researcher searches, then reviewer checks, then gatherer writes.

    The agents run in that order. Each one receives the previous agent's text.
    The run does not depend on an agent choosing to hand off.
    """
    builder = GraphBuilder()
    builder.add_node(_researcher(), "researcher")
    builder.add_node(_reviewer(), "reviewer")
    builder.add_node(_gatherer(), "gatherer")
    builder.add_edge("researcher", "reviewer")
    builder.add_edge("reviewer", "gatherer")
    builder.set_entry_point("researcher")
    builder.set_max_node_executions(6)
    builder.set_execution_timeout(1500.0)
    builder.set_node_timeout(600.0)
    return builder.build()


def _failure_reason(result: MultiAgentResult) -> str:
    """Name the status and the agents that actually ran."""
    finished = ", ".join(result.results) or "no agent"
    problems = [
        f"{name} failed: {node_result}"
        for name, node_result in result.results.items()
        if node_result.status is not Status.COMPLETED
    ]
    detail = f" {' '.join(problems)}" if problems else ""
    return f"Research stopped with status {result.status.value} after {finished}.{detail}"


def split_report(text: str) -> ResearchReport:
    """Split a gatherer response on the Short and Sources headings."""
    short = _section(text, "Short")
    long = _section(text, "Sources") or _section(text, "Long")
    if not short:
        short = text.strip()
    if not long:
        long = text.strip()
    return ResearchReport(short=short, long=long, full=text.strip())


def _researcher() -> Agent:
    return Agent(
        name="researcher",
        description="Searches the public web once and returns a few claims with source URLs.",
        model=_nova(temperature=0.1, max_tokens=2048),
        tools=[web_search],
        system_prompt=_read("researcher.md"),
        callback_handler=None,
    )


def _reviewer() -> Agent:
    # Low extended thinking is enough for a short packet check.
    # Temperature must stay unset while reasoning effort is on.
    return Agent(
        name="reviewer",
        description="Checks each claim against the search packet and drops anything unsupported.",
        model=_nova(
            additional_request_fields={
                "reasoningConfig": {"type": "enabled", "maxReasoningEffort": "low"}
            },
        ),
        tools=[web_fetch, web_search],
        system_prompt=_read("reviewer.md"),
        callback_handler=None,
    )


def _gatherer() -> Agent:
    return Agent(
        name="gatherer",
        description="Writes a short spoken brief and a short sources list from verified claims.",
        model=_nova(temperature=0.3, max_tokens=2000),
        system_prompt=_read("gatherer.md"),
        callback_handler=None,
    )


def _nova(
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
    additional_request_fields: dict[str, object] | None = None,
) -> BedrockModel:
    settings: dict[str, object] = {}
    if temperature is not None:
        settings["temperature"] = temperature
    if max_tokens is not None:
        settings["max_tokens"] = max_tokens
    if additional_request_fields is not None:
        settings["additional_request_fields"] = additional_request_fields
    return BedrockModel(model_id=NOVA_2_LITE, region_name=aws_region(), **settings)


def _read(name: str) -> str:
    return (_PROMPTS / name).read_text(encoding="utf-8").strip()


def _section(text: str, heading: str) -> str:
    marker = f"## {heading}"
    start = text.find(marker)
    if start < 0:
        return ""
    body = text[start + len(marker) :]
    next_heading = body.find("\n## ")
    if next_heading >= 0:
        body = body[:next_heading]
    return body.strip()
