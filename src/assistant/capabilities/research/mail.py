"""Send a research report through Amazon SES."""

import os
from pathlib import Path

import boto3

from hello_world_voice.config import aws_region

def email_recipient() -> str | None:
    """Return ASSISTANT_EMAIL_TO, or None when it is unset."""
    recipient = os.environ.get("ASSISTANT_EMAIL_TO", "").strip()
    return recipient or None


def send_research(path: Path) -> str:
    """Email one research report. Returns the sentence Bob should speak."""
    recipient = email_recipient()
    if recipient is None:
        return "Set ASSISTANT_EMAIL_TO to the verified SES address before sending research."
    sender = os.environ.get("ASSISTANT_EMAIL_FROM", "").strip() or recipient
    _ses_send(sender, recipient, _subject(path), path.read_text(encoding="utf-8"))
    return f"Sent the research to {recipient}."


def _subject(path: Path) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        return "Research report"
    first = lines[0].removeprefix("# ").strip()
    return first or "Research report"


def _ses_send(sender: str, recipient: str, subject: str, body: str) -> None:
    client = boto3.client("ses", region_name=aws_region())
    client.send_email(
        Source=sender,
        Destination={"ToAddresses": [recipient]},
        Message={
            "Subject": {"Data": subject, "Charset": "UTF-8"},
            "Body": {"Text": {"Data": body, "Charset": "UTF-8"}},
        },
    )
