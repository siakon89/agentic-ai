"""Search the public web with Amazon Nova Grounding."""

from typing import Any

import boto3
from botocore.config import Config
from strands import tool

from meeting_listener.config import aws_region

# Nova 2 Lite is the only Nova model with the nova_grounding system tool.
# Web Grounding is served from US cross-region inference profiles.
NOVA_2_LITE = "us.amazon.nova-2-lite-v1:0"


@tool
def web_search(query: str) -> str:
    """Search the public web and return findings with source URLs.

    Args:
        query: The question to look up.
    """
    client = boto3.client(
        "bedrock-runtime",
        region_name=aws_region(),
        config=Config(read_timeout=180),
    )
    response = client.converse(
        modelId=NOVA_2_LITE,
        messages=[{"role": "user", "content": [{"text": query}]}],
        toolConfig={"tools": [{"systemTool": {"name": "nova_grounding"}}]},
    )
    return text_from_grounded_response(response)


def text_from_grounded_response(response: dict[str, Any]) -> str:
    """Join the grounded answer and the citation URLs."""
    content = response.get("output", {}).get("message", {}).get("content", [])
    parts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        text = block.get("text")
        if isinstance(text, str) and text.strip():
            parts.append(text.strip())
        for url in _citation_urls(block.get("citationsContent")):
            parts.append(f"Source: {url}")
    if not parts:
        return "The search returned no text."
    return "\n".join(parts)


def _citation_urls(citations_content: object) -> list[str]:
    if not isinstance(citations_content, dict):
        return []
    urls: list[str] = []
    for citation in citations_content.get("citations", []):
        if not isinstance(citation, dict):
            continue
        url = citation.get("location", {}).get("web", {}).get("url")
        if isinstance(url, str) and url:
            urls.append(url)
    return urls
