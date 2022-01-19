"""Mapdiff command."""


from dataclasses import dataclass
from io import TextIOBase
from typing import Dict, Iterator, List, Union

from .common import ValidationException, textiter

Source = Union[str, Iterator[str], TextIOBase]


@dataclass
class Arguments:
    """
    Arguments of `Runner`.

    :left: left file
    :right: right file
    :key: key field
    :delimiter: field delimiter character
    :with_no_diff: yield even if no diff
    """

    left: Source
    right: Source
    key: int = 0
    delimiter: str = " "
    with_no_diff: bool = False

    def runner(self) -> "Runner":
        """Return a new `Runner`."""
        return Runner(self)


class InvalidDelimiterError(ValidationException):
    """Raised when the delimiter is invalid for setdiff."""


class NoKeyError(ValidationException):
    """Raised when a source has a row without the key column."""


class DuplicatedKeyError(ValidationException):
    """Raised when a source has duplicated keys."""


@dataclass
class Runner:
    """Diff by key."""

    args: Arguments

    def run(self) -> Iterator[str]:
        """Run mapdiff."""
        if len(self.args.delimiter) != 1:
            raise InvalidDelimiterError(self.args.delimiter)

        left = self.__compact(self.args.left, "left")
        right = self.__compact(self.args.right, "right")
        for k in {*left.keys(), *right.keys()}:
            a, b = left.get(k), right.get(k)
            if b is None:
                yield f"< {a}"
                continue
            if a is None:
                yield f"> {b}"
                continue
            if a != b:
                yield f"<>< {a}"
                yield f"<>> {b}"
                continue
            if self.args.with_no_diff:
                yield a

    def __compact(self, src: Source, target: str) -> Dict[str, str]:
        r: Dict[str, str] = {}
        for i, x in enumerate(self.__split(src)):
            if self.args.key < 0 or self.args.key >= len(x):
                raise NoKeyError(f"{target} at line {i+1}")
            k = x[self.args.key]
            if k in r:
                raise DuplicatedKeyError(f"{target} at line {i+1}")
            r[k] = self.args.delimiter.join(x)
        return r

    def __split(self, src: Source) -> List[List[str]]:
        return list(x.rstrip().split(self.args.delimiter) for x in textiter(src))
