"""CSVCut Command."""


import csv
from dataclasses import dataclass
from io import TextIOBase
from typing import IO, Iterator, List, Optional, Union

from .common import CSVWriter, JSONWriter, StructWriter, ValidationException, textiter

Source = Union[str, Iterator[str], TextIOBase]


@dataclass
class Range:
    """Target range."""

    start: Optional[int] = None
    end: Optional[int] = None


@dataclass
class Target:
    """Range list."""

    target: List[Range]

    def select(self, row: List[str]) -> List[str]:
        """Select the specified columns from the row."""
        r: List[str] = []
        for t in self.target:
            s, e = t.start, t.end
            if s and e:
                r.extend(row[s - 1 : e])
                continue
            if s:
                r.extend(row[s - 1 :])
                continue
            if e:
                r.extend(row[:e])
        return r


class InvalidTargetError(ValidationException):
    """Raise when target string is invalid."""


class TargetParser:
    """Parse the target string.""" ""

    @classmethod
    def parse(cls, val: str) -> Target:
        r"""Parse val into `Target`.

        >>> from pytools import csvcut
        >>> csvcut.TargetParser.parse("1").target
        [Range(start=1, end=1)]
        >>> csvcut.TargetParser.parse("1-3").target
        [Range(start=1, end=3)]
        >>> csvcut.TargetParser.parse("1,8-").target
        [Range(start=1, end=1), Range(start=8, end=None)]
        >>> csvcut.TargetParser.parse("-7,10,13").target
        [Range(start=None, end=7), Range(start=10, end=10), Range(start=13, end=13)]
        """
        try:
            return cls.__parse(val)
        except Exception as e:
            raise InvalidTargetError(val) from e

    @classmethod
    def __parse(cls, val: str) -> Target:
        return Target([cls.__parse_range(x) for x in val.split(",")])

    @staticmethod
    def __parse_range(val: str) -> Range:
        seed = val.split("-")
        if len(seed) == 1:
            p = int(seed[0])
            return Range(start=p, end=p)
        if len(seed) == 2:
            x, y = seed[0], seed[1]
            if not y:
                return Range(start=int(x))
            if not x:
                return Range(end=int(y))
            return Range(start=int(x), end=int(y))
        raise Exception(f"invalid range: {val}")


@dataclass
class Arguments:
    """
    Arguments of `Runner`.

    :target: target expression, like 1-3,5
    :source: source text stream.
    :destination: output text stream.
    :headers_included: if true, input line 1 as headers.
    :headers: provide headers, like id,name,created_at.
        This overwrites the original headers.
    :delimiter: output delimiter.
    :as_json: if true, output as json.
    """

    target: str
    source: Source
    destination: IO
    headers_included: bool
    headers: Optional[str] = None
    delimiter: str = ","
    as_json: bool = False

    def runner(self) -> "Runner":
        """Return a new `Runner`."""
        return Runner(self)


class InvalidHeadersError(ValidationException):
    """Raise when the specified headers are invalid."""


@dataclass
class Runner:
    """Select columns from csv input."""

    args: Arguments

    @staticmethod
    def __new_writer(
        dest: TextIOBase, as_json: bool, headers: Optional[List[str]], delimiter=","
    ) -> StructWriter:
        if as_json:
            return JSONWriter(dest, headers)
        return CSVWriter(dest, headers, delimiter)

    @staticmethod
    def __parse_target(val: str) -> Target:
        return TargetParser.parse(val)

    @staticmethod
    def __parse_headers(val: str) -> List[str]:
        headers = val.split(",")
        if any(len(x) == 0 for x in headers):
            raise InvalidHeadersError(val)
        return headers

    @classmethod
    def __new_headers(
        cls, src: Optional[Iterator[str]], headers: Optional[str]
    ) -> Optional[List[str]]:
        if src:
            return cls.__parse_headers(src.__next__())
        if headers:
            return cls.__parse_headers(headers)
        return None

    def run(self):
        """Run csvcut."""
        target = self.__parse_target(self.args.target)
        src = textiter(self.args.source)
        headers = self.__new_headers(
            src if self.args.headers_included else None,
            self.args.headers,
        )
        reader = csv.reader(src)
        writer = self.__new_writer(
            self.args.destination, self.args.as_json, headers, self.args.delimiter
        )

        for row in reader:
            writer.write(target.select(row))
