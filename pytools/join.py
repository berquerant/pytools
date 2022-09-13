"""Join command."""

import sys
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, Iterator, Optional, TextIO, Tuple, Union, cast

import pyparsing as pp

from .common import ValidationException, json_dumps
from .log import debug, with_debug


@dataclass
class Location:
    """Source number and column number."""

    src: int
    col: int

    def add_col(self, diff: int) -> "Location":
        """Return new `Location` that added diff to col."""
        return Location(src=self.src, col=self.col + diff)

    def set_col(self, col: int) -> "Location":
        """Return new `Location` that set col."""
        return Location(src=self.src, col=col)

    def add_src(self, diff: int) -> "Location":
        """Return new `Location` that added diff to src."""
        return Location(src=self.src + diff, col=self.col)

    def add(self, src_diff: int, col_diff: int) -> "Location":
        """Return new `Location` that added src_diff to src and col_diff to col."""
        return Location(src=self.src + src_diff, col=self.col + col_diff)


Ends = Tuple[Location, Location]


class Range(ABC):
    """Selected portion."""

    @abstractmethod
    def ends(self) -> Ends:
        """Return the zero-based location boundaries."""


@dataclass
class Single(Range):
    """Single column."""

    loc: Location

    def ends(self) -> Ends:  # noqa: D102
        return self.loc.add(-1, -1), self.loc


@dataclass
class Left(Range):
    """Left limited range."""

    loc: Location

    def ends(self) -> Ends:  # noqa: D102
        return self.loc.add(-1, -1), self.loc.set_col(sys.maxsize)


@dataclass
class Right(Range):
    """Right limited range."""

    loc: Location

    def ends(self) -> Ends:  # noqa: D102
        return self.loc.set_col(0).add_src(-1), self.loc


@dataclass
class Interval(Range):
    """Inclusive interval."""

    left: Location
    right: Location

    def ends(self) -> Ends:  # noqa: D102
        return self.left.add(-1, -1), self.right


Target = list[Range]
JoinKey = Interval


class Parser:
    """Parses DSL to join like `cut` options."""

    @staticmethod
    def __to_location(xs: list[str]) -> Location:
        try:
            if len(xs) != 3:
                raise Exception("Invalid location format")
            src = int(xs[0])
            if src < 1:
                raise Exception("Non natural src")
            col = int(xs[2])
            if col < 1:
                raise Exception("Non natural col")
            return Location(src=src, col=col)
        except Exception as e:
            data = "".join(xs)
            raise ValidationException(f"Invalid location: {data}") from e

    @staticmethod
    def __to_strlist(x: Any) -> list[str]:
        return cast(list[str], x)

    @classmethod
    def __to_interval(cls, xs: list[Union[list[str], str]]) -> Interval:
        slist = cls.__to_strlist
        to_location = cls.__to_location

        try:
            if len(xs) != 3:
                raise Exception("Invalid interval range")
            left = to_location(slist(xs[0]))
            right = to_location(slist(xs[2]))
            return Interval(left=left, right=right)
        except Exception as e:
            data = json_dumps(xs)
            raise ValidationException(f"Invalid interval: {data}") from e

    @classmethod
    def __to_range(cls, xs: list[Union[list[str], str]]) -> Range:
        slist = cls.__to_strlist
        to_location = cls.__to_location

        try:
            match len(xs):
                case 1:
                    return Single(to_location(slist(xs[0])))
                case 3:
                    return cls.__to_interval(xs)
                case 2:
                    if xs[0] == "-":
                        return Right(to_location(slist(xs[1])))
                    if xs[1] == "-":
                        return Left(to_location(slist(xs[0])))
                    raise Exception("Invalid left or right")
                case _:
                    raise Exception("Unknown range")
        except Exception as e:
            data = json_dumps(xs)
            raise ValidationException(f"Invalid range: {data}") from e

    @classmethod
    def parse_target(cls, value: str) -> Target:
        """
        Parse value as target.

        natural := natural number
        location := natural "." natural  // source . column
        single := location
        left := location "-"
        right := "-" location
        interval := location "-" location
        range := interval | right | left | single
        target := range {"," range}
        """
        natural = pp.common.integer
        location = pp.Group(natural + "." + natural)
        single = location
        left = location + "-"
        right = "-" + location
        interval = location + "-" + location
        rng = pp.Group(interval ^ right ^ left ^ single)
        target = pp.delimited_list(rng)

        try:
            return [
                cls.__to_range(x)
                for x in target.parse_string(value, parse_all=True).as_list()
            ]
        except Exception as e:
            raise ValidationException(f"Parse target error: {value}") from e

    @classmethod
    def parse_joinkey(cls, value: str) -> JoinKey:
        """
        Parse value as joinkey.

        natural := natural number
        location := natural "." natural  // source . column
        interval := location "-" location
        """
        natural = pp.common.integer
        location = pp.Group(natural + "." + natural)
        relation = location + "=" + location

        try:
            r = cls.__to_interval(
                relation.parse_string(value, parse_all=True).as_list()
            )
            if r.left.src == r.right.src:
                raise Exception("JoinKey has the same src")
            return r
        except Exception as e:
            raise ValidationException(f"Parse joinkey error: {value}") from e


IndexKey = Callable[[str], str]


@dataclass
class IndexItem:
    """Data to register to `Index`."""

    key: str
    offset: int


IndexItemList = list[IndexItem]


class Index:
    """In-memory word-to-lines index."""

    def __init__(self, src: TextIO):
        """
        Return new `Index`.

        :src: seekable
        """
        self.__index: dict[str, IndexItemList] = defaultdict(list)
        self.__src = src

    def add(self, item: IndexItem):
        """Add new item."""
        self.__index[item.key].append(item)

    def get(self, key: str) -> Optional[list[str]]:
        """Find lines with key."""
        items = self.__index.get(key)
        if not items:
            return None

        def seek(offset: int) -> str:
            self.__src.seek(offset, 0)
            return self.__src.readline().rstrip()

        return [seek(x.offset) for x in items]

    @staticmethod
    def new(src: TextIO, key: IndexKey) -> "Index":
        """
        Return new `Index`.

        :src: seekable
        """
        if not src.seekable():
            raise ValidationException("Index requires seekable source")
        index = Index(src)
        while True:
            offset = src.tell()
            line = src.readline()
            if line == "":
                return index
            index.add(
                IndexItem(
                    key=key(line.rstrip()),
                    offset=offset,
                )
            )


@with_debug
def select_columns(target: Target, column_list: list[list[str]]) -> list[str]:
    """Select columns from column_list via target."""

    def in_src_range(src: int) -> bool:
        return 0 <= src < len(column_list)

    @with_debug
    def select(rng: Range) -> list[str]:
        l, r = rng.ends()
        if not (in_src_range(l.src) and in_src_range(r.src - 1)):
            raise Exception("Out of source range")

        srcs = column_list[l.src : r.src]
        match len(srcs):
            case 0:
                return []
            case 1:
                return srcs[0][l.col : r.col]
            case 2:
                return srcs[0][l.col :] + srcs[1][: r.col]
            case x:
                return (
                    srcs[0][l.col :]
                    + sum(srcs[1 : r.src - 1], [])
                    + srcs[x - 1][: r.col]
                )

    return sum([select(x) for x in target], [])


class Joiner:
    """Join data sources."""

    def __init__(self, src1: TextIO, src2: TextIO):
        """
        Return new `Joiner`.

        :src2: seekable
        """
        self.src1 = src1
        self.src2 = src2

    def join(self, key: JoinKey, delimiter: str, target: Target) -> Iterator[str]:
        """Join 2 sources with the specified key and yield the columns that selected by target."""
        lkey, rkey = key.left.add(-1, -1), key.right.add(-1, -1)
        debug("lkey %s rkey %s", lkey, rkey)

        def is_valid_key() -> bool:
            return lkey.src in [0, 1] and rkey.src in [0, 1] and lkey.src != rkey.src

        def sorted_key_cols() -> Tuple[int, int]:
            if lkey.src == 0:  # left is src1
                return lkey.col, rkey.col
            # right is src1
            return rkey.col, lkey.col

        def new_key(x: str, col: int) -> str:
            try:
                return x.split(delimiter)[col]
            except Exception as e:
                raise Exception(f"New key from {x}, col {col}") from e

        try:
            if not is_valid_key:
                raise Exception("Invalid JoinKey")
            s1col, s2col = sorted_key_cols()
            debug("src1 col %d src2 col %d", s1col, s2col)
            index = Index.new(self.src2, lambda x: new_key(x, s2col))
            for line in self.src1:
                xs = line.rstrip().split(delimiter)
                if not 0 <= s1col < len(xs):
                    raise Exception(f"Out of range {s2col} in {line.rstrip()}")

                k = xs[s1col]
                debug("index key %s => %s", k, xs)
                idx_lines = index.get(k)
                if idx_lines is None:
                    continue
                for line in idx_lines:
                    idx_cols = line.split(delimiter)
                    debug("got by index: %s", idx_cols)
                    yield delimiter.join(select_columns(target, [xs, idx_cols]))

        except Exception as e:
            raise ValidationException("Join failed") from e


@dataclass
class Arguments:
    """
    Arguments of `Runner`.

    :sources: data sources
    :delimiter: column delimiter
    :joinkey: join spec
    :target: target expression
    """

    sources: list[TextIO]
    delimiter: str
    joinkey: str
    target: str

    def runner(self) -> "Runner":
        """Return a new `Runner`."""
        debug(
            "Options: delimiter(%s) joinkey(%s) target(%s)",
            self.delimiter,
            self.joinkey,
            self.target,
        )
        if len(self.sources) != 2:
            raise ValidationException("Require just 2 sources")
        return Runner(self)


@dataclass
class Runner:
    """Join data sources."""

    args: Arguments

    def run(self) -> Iterator[str]:
        """Run join."""
        key = Parser.parse_joinkey(self.args.joinkey)
        target = Parser.parse_target(self.args.target)
        yield from Joiner(self.args.sources[0], self.args.sources[1]).join(
            key, self.args.delimiter, target
        )
