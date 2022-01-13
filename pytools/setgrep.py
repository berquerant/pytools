"""Setgrep command."""


from dataclasses import dataclass
from io import TextIOBase
from typing import Iterator, Union

from .common import textiter

Source = Union[str, Iterator[str], TextIOBase]


@dataclass
class Arguments:
    """
    Arguments of `Runner`.

    :target: materials of set for grep
    :source: grep target
    """

    target: Source
    source: Source

    def runner(self) -> "Runner":
        """Return a new `Runner`."""
        return Runner(self)


@dataclass
class Runner:
    """Grep by set."""

    args: Arguments

    def run(self) -> Iterator[str]:
        """Run setgrep."""
        tset = set(x.rstrip() for x in textiter(self.args.target))
        for line in textiter(self.args.source):
            for t in tset:
                if t in line:
                    yield line
