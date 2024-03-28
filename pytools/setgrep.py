"""Setgrep command."""

from dataclasses import dataclass
from io import TextIOBase
from typing import Iterator, Optional, Union

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
    max_matches: int = 0
    perfect: bool = False

    def runner(self) -> "Runner":
        """Return a new `Runner`."""
        return Runner(self)


@dataclass
class Match:
    """Matched line and match target."""

    line: str
    target: str


class Seed:
    """Set of targets."""

    def __init__(self, values: set[str], perfect: bool):
        """
        Return a new `Seed`.

        :values: contents of the seed
        :perfect: perfect match or not
        """
        self.values = values
        self.perfect = perfect

    def find(self, line: str) -> Optional[Match]:
        """Find a target in the line."""
        if self.perfect:
            if line.rstrip() in self.values:
                return Match(line=line, target=line)
            return None
        for v in self.values:
            if v in line:
                return Match(line=line, target=v)
        return None

    def remove(self, target: str):
        """Remove the target from seed."""
        self.values.remove(target)


class Matcher:
    """Do matching and seed management."""

    def __init__(self, seed: Seed, max_matches: int):
        """
        Return a new `Matcher`.

        :seed: seed
        :max_matches: limit of match count, non-positive is no limit.
        """
        self.seed = seed
        self.matches: dict[str, int] = {}
        self.max_matches = max_matches

    @property
    def max_matches_enabled(self) -> bool:
        """Limit max match count or not."""
        return self.max_matches > 0

    def match(self, line: str) -> Optional[Match]:
        """Find a target in the line."""
        m = self.seed.find(line)
        if not m:
            return None
        if not self.max_matches_enabled:
            return m
        c = self.matches.get(m.target, 0)
        if c >= self.max_matches:  # banned
            del self.matches[m.target]
            self.seed.remove(m.target)
            return None
        self.matches[m.target] = c + 1
        return m


@dataclass
class Runner:
    """Grep by set."""

    args: Arguments

    def run(self) -> Iterator[str]:
        """Run setgrep."""
        seed = Seed(
            set(x.rstrip() for x in textiter(self.args.target)), self.args.perfect
        )
        matcher = Matcher(seed, self.args.max_matches)
        for line in textiter(self.args.source):
            m = matcher.match(line)
            if m:
                yield line
