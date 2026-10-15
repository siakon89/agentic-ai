"""Environment settings shared by the voice session and the notes model."""

import os

DEFAULT_VOICE_MODEL_ID = "amazon.nova-2-5-sonic"
DEFAULT_NOTES_MODEL_ID = "amazon.nova-lite-v1:0"


def aws_region() -> str:
    """Region for the notes model and SES."""
    return os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"


def research_region() -> str:
    """Region for Nova Web Grounding only.

    Grounding still needs a US CRIS call, so this defaults to ``us-east-1``.
    Research agents themselves use ``AWS_REGION`` with the global Nova 2 Lite
    profile. Override with ``RESEARCH_REGION`` if needed.
    """
    return os.environ.get("RESEARCH_REGION") or "us-east-1"


def sonic_region() -> str:
    """Region for Nova Sonic. Stockholm is the default."""
    return os.environ.get("SONIC_REGION") or "eu-north-1"


def voice_model_id() -> str:
    return os.environ.get("VOICE_MODEL_ID", DEFAULT_VOICE_MODEL_ID)


def notes_model_id() -> str:
    return os.environ.get("NOTES_MODEL_ID", DEFAULT_NOTES_MODEL_ID)
