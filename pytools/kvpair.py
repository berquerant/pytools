"""KVPair command."""

from dataclasses import dataclass
from typing import Iterator


@dataclass
class Pair:
    """Key-Value pair."""

    key: str
    value: str


class Pairs:
    """List of `Pair`."""

    def __init__(self):
        """Return a new `Pairs`."""
        self.__pairs: dict[str, Pair] = {}

    def __iter__(self) -> Iterator[Pair]:  # noqa: D105
        return iter(self.__pairs.values())

    def add(self, pair: Pair):
        """Add a Pair to the list."""
        self.__pairs[pair.key] = pair

    @staticmethod
    def loads(val: str) -> "Pairs":
        """Convert key-value pairs to `Pairs`."""
        pairs = Pairs()
        for v in val.split(" "):
            xs = v.split("=")
            if len(xs) != 2:
                continue
            pairs.add(Pair(key=xs[0], value=xs[1]))
        return pairs


@dataclass
class Arguments:
    """Arguments of `Runner`."""

    src: Iterator[str]

    def runner(self) -> "Runner":
        """Return a new `Runner`."""
        return Runner(self)


@dataclass
class Runner:
    """KVPair."""

    args: Arguments

    def run(self) -> Iterator[Pairs]:
        """Run kvpair."""
        for line in self.args.src:
            yield Pairs.loads(line)
