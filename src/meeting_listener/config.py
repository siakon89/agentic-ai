"""Environment settings shared by the voice session and the notes model."""

import os

DEFAULT_VOICE_MODEL_ID = "amazon.nova-2-5-sonic"
DEFAULT_NOTES_MODEL_ID = "amazon.nova-lite-v1:0"


def aws_region() -> str:
    """Region for Nova Sonic and the notes model."""
    return os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"


def voice_model_id() -> str:
    return os.environ.get("VOICE_MODEL_ID", DEFAULT_VOICE_MODEL_ID)


def notes_model_id() -> str:
    return os.environ.get("NOTES_MODEL_ID", DEFAULT_NOTES_MODEL_ID)
