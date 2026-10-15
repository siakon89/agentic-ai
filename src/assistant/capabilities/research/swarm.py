"""A three-agent swarm that researches a topic on the public web."""

from dataclasses import dataclass
from pathlib import Path

from strands import Agent
from strands.models import BedrockModel
from strands.multiagent import Swarm
from strands.multiagent.base import Status
from strands.vended_tools import web_fetch

from assistant.capabilities.research.search import NOVA_2_LITE, web_search
from meeting_listener.config import aws_region

_PROMPTS = Path(__file__).parent / "prompts"


@dataclass(frozen=True)
class ResearchReport:
    """The gatherer's short brief and long article."""

    short: str
    long: str
    full: str


def run_research(topic: str) -> ResearchReport:
    """Run researcher, reviewer, and gatherer, then return both lengths."""
    swarm = build_research_swarm()
    result = swarm(
        "Research this topic on the public web. "
        "The researcher searches, the reviewer checks the claims, "
        "and the gatherer writes the short and long pieces.\n\n"
        f"Topic: {topic}"
    )
    if result.status is not Status.COMPLETED:
        raise RuntimeError(f"Research swarm finished with status {result.status.value}.")
    if "gatherer" not in result.results:
        raise RuntimeError("The research swarm finished before the gatherer wrote the report.")
    return split_report(str(result.results["gatherer"]))


def build_research_swarm() -> Swarm:
    """Researcher searches, reviewer checks, gatherer writes."""
    researcher = _researcher()
    return Swarm(
        [researcher, _reviewer(), _gatherer()],
        entry_point=researcher,
        max_handoffs=4,
        max_iterations=6,
        execution_timeout=1500.0,
        node_timeout=600.0,
    )


def split_report(text: str) -> ResearchReport:
    """Split a gatherer response on the Short and Long headings."""
    short, long = _section(text, "Short"), _section(text, "Long")
    if not short:
        short = text.strip()
    if not long:
        long = text.strip()
    return ResearchReport(short=short, long=long, full=text.strip())


def _researcher() -> Agent:
    return Agent(
        name="researcher",
        description="Searches the public web and returns claims with source URLs.",
        model=_nova(temperature=0.1),
        tools=[web_search],
        system_prompt=_read("researcher.md"),
        callback_handler=None,
    )


def _reviewer() -> Agent:
    # High extended thinking is Nova 2 Lite's setting for checking conclusions.
    # Temperature must stay unset while that effort level is on.
    return Agent(
        name="reviewer",
        description="Checks each claim against its source and drops anything unsupported.",
        model=_nova(
            additional_request_fields={
                "reasoningConfig": {"type": "enabled", "maxReasoningEffort": "high"}
            }
        ),
        tools=[web_fetch, web_search],
        system_prompt=_read("reviewer.md"),
        callback_handler=None,
    )


def _gatherer() -> Agent:
    return Agent(
        name="gatherer",
        description="Writes a short spoken brief and a long article from verified claims.",
        model=_nova(temperature=0.3, max_tokens=8000),
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
