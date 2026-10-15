"""Pass Bob's replies through only after the user says his name."""

from strands.bidi.types.io import InputStream, OutputStream

from hello_world_voice.address import AddressGate as _AddressGate
from hello_world_voice.address import guard as _guard


class AddressGate(_AddressGate):
    """Remember whether the current turn addressed Bob by name."""

    def __init__(self) -> None:
        super().__init__("Bob")


def guard(
    inputs: list[InputStream],
    outputs: list[OutputStream],
) -> tuple[list[InputStream], list[OutputStream]]:
    """Share one gate across the session's input and output streams."""
    return _guard(inputs, outputs, name="Bob")
