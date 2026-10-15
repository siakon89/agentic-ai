"""Send a research report through Amazon SES."""

import os
from pathlib import Path

import boto3

from meeting_listener.config import aws_region

# Verified SES identity for this project. Override with ASSISTANT_EMAIL_TO.
DEFAULT_RECIPIENT = "siaterliskonsta@gmail.com"


def email_recipient() -> str:
    return os.environ.get("ASSISTANT_EMAIL_TO", DEFAULT_RECIPIENT)


def send_research(path: Path) -> str:
    """Email one research report. Returns the sentence Ultron should speak."""
    recipient = email_recipient()
    sender = os.environ.get("ASSISTANT_EMAIL_FROM", recipient)
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
