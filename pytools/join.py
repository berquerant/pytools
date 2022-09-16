"""Join command."""

import sys
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    Iterator,
    Optional,
    Sequence,
    TextIO,
    Tuple,
    Union,
    cast,
)

import pyparsing as pp

from .common import ValidationException, json_dumps
from .log import debug, with_debug


@dataclass(frozen=True)  # hashable
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
JoinKeyRelation = Interval
JoinKey = list[JoinKeyRelation]


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
    def __cast_to_strlist(x: Any) -> list[str]:
        return cast(list[str], x)

    @classmethod
    def __to_interval(cls, xs: list[Union[list[str], str]]) -> Interval:
        slist = cls.__cast_to_strlist
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
        slist = cls.__cast_to_strlist
        to_location = cls.__to_location

        try:
            match len(xs):
                case 1:
                    return Single(to_location(slist(xs[0])))
                case 2:
                    if xs[0] == "-":
                        return Right(to_location(slist(xs[1])))
                    if xs[1] == "-":
                        return Left(to_location(slist(xs[0])))
                    raise Exception("Invalid left or right")
                case 3:
                    return cls.__to_interval(xs)
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
        relation := location "=" location
        joinkey := relation {"," relation}
        """
        natural = pp.common.integer
        location = pp.Group(natural + "." + natural)
        relation = pp.Group(location + "=" + location)
        joinkey = pp.delimited_list(relation)

        try:
            r = [
                cls.__to_interval(x)
                for x in joinkey.parse_string(value, parse_all=True).as_list()
            ]
            for x in r:
                if x.left.src == x.right.src:
                    raise Exception("Some join key relations have the same src")
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


@dataclass
class ScannedIndexItem:
    """Data read from `Index`."""

    line: str
    index: IndexItem


class Index:
    """In-memory word-to-lines index."""

    def __init__(self, src: TextIO, key: IndexKey):
        """
        Return a new `Index`.

        :src: seekable
        :key: function to generate key
        """
        self.__index: dict[str, IndexItemList] = defaultdict(list)
        self.__src = src
        self.__key = key

    @property
    def key(self) -> IndexKey:
        """Return the function to generate key."""
        return self.__key

    def add(self, item: IndexItem):
        """Add a new item."""
        self.__index[item.key].append(item)

    def read(self, item: IndexItem) -> ScannedIndexItem:
        """Read a line at the item."""
        self.__src.seek(item.offset, 0)
        return ScannedIndexItem(
            line=self.__src.readline().rstrip(),
            index=item,
        )

    def get(self, key: str) -> Optional[list[IndexItem]]:
        """Find items with key."""
        items = self.__index.get(key)
        if not items:
            if items is not None:
                del self.__index[key]
            return None
        return items

    def delete(self, item: IndexItem):
        """Delete an item."""
        items = self.__index.get(item.key)
        if not items:
            if items is not None:
                del self.__index[item.key]
            return
        try:
            items.remove(item)
        except ValueError:
            pass

    def items(self) -> Iterator[IndexItem]:
        """Yield all index items."""
        for items in self.__index.values():
            yield from items

    def scan(self) -> Iterator[ScannedIndexItem]:
        """Yield all lines."""
        for items in self.__index.values():
            for item in items:
                self.__src.seek(item.offset, 0)
                yield ScannedIndexItem(
                    line=self.__src.readline().rstrip(),
                    index=item,
                )

    @staticmethod
    def new(src: TextIO, key: IndexKey) -> "Index":
        """
        Return a new `Index`.

        :src: seekable
        :key: function to generate key
        """
        if not src.seekable():
            raise ValidationException("Index requires seekable source")
        src.seek(0, 0)
        index = Index(src, key)
        while True:
            offset = src.tell()
            line = src.readline()
            if line == "":
                return index
            line = line.rstrip()
            k = key(line)
            debug("New IndexItem: key %s line %s offset %d", k, line, offset)
            index.add(
                IndexItem(
                    key=k,
                    offset=offset,
                )
            )


class IndexCache:
    """Cache of `Index`."""

    def __init__(self, srcs: Sequence[TextIO]):
        """
        Return a new `IndexCache`.

        :srcs: seekable data sources
        """
        self.__cache: dict[Location, Index] = {}
        self.__srcs = srcs

    @staticmethod
    def __index_key(col: int, delimiter: str) -> IndexKey:
        def key(line: str) -> str:
            try:
                return line.split(delimiter)[col]
            except Exception as e:
                raise Exception(f"New key from {line}, col {col}") from e

        return key

    def get(self, loc: Location, delimiter: str) -> Index:
        """
        Get `Index`.

        Construct `Index` if not cached.
        :loc: index location
        :delimiter: column delimiter
        """
        if loc not in self.__cache:
            debug("New missing Index: loc %s delimiter %s", loc, delimiter)
            if not 0 <= loc.src < len(self.__srcs):
                raise Exception(f"Out of range: {loc}")
            self.__cache[loc] = Index.new(
                self.__srcs[loc.src], self.__index_key(loc.col, delimiter)
            )
        return self.__cache[loc]


@dataclass
class JoinItem:
    """Selected line of a source."""

    src: int  # zero-based
    index: IndexItem


class JoinItemList:
    """Selected parts of sources."""

    def __init__(self, items: Optional[list[JoinItem]] = None):
        """Rerturn a new `JoinItemList`."""
        self.__items: dict[int, JoinItem] = (
            {} if items is None else {x.src: x for x in items}
        )

    def get(self, src: int) -> Optional[JoinItem]:
        """Return an item of the `src`-th source."""
        return self.__items.get(src)

    def set(self, item: JoinItem):
        """Register an item."""
        self.__items[item.src] = item

    def items(self) -> Iterator[JoinItem]:
        """Yield all items in src asc order."""
        for src in sorted(self.__items):
            yield self.__items[src]

    def keys(self) -> Iterator[int]:
        """Yield all src numbers in asc order."""
        yield from sorted(self.__items)

    def copy(self) -> "JoinItemList":
        """Return a shallow copy of this."""
        return JoinItemList(list(self.__items.values()))

    def __str__(self) -> str:
        """Return a string expression."""
        return str(list(self.items()))


JoinResult = list[JoinItemList]


class RelationJoiner:
    """Resolve `JoinKeyRelation`."""

    def __init__(self, cache: IndexCache, delimiter: str):
        """
        Return a new `RelationJoiner`.

        :cache: index cache
        :delimiter: column delimiter
        """
        self.__cache = cache
        self.__delimiter = delimiter

    def __get_index(self, loc: Location) -> Index:
        try:
            return self.__cache.get(loc, self.__delimiter)
        except Exception as e:
            raise Exception(f"Missing index: {loc}") from e

    def __full_join(self, rel: JoinKeyRelation) -> Iterator[JoinItemList]:
        lkey, rkey = rel.left.add(-1, -1), rel.right.add(-1, -1)
        lindex, rindex = self.__get_index(lkey), self.__get_index(rkey)

        # cross join for all lines
        for litem in lindex.items():
            ritems = rindex.get(litem.key)
            if not ritems:
                continue

            r = JoinItemList()
            r.set(JoinItem(src=lkey.src, index=litem))
            for ritem in ritems:
                p = r.copy()
                p.set(JoinItem(src=rkey.src, index=ritem))
                debug(
                    "Full join: lkey %s rkey %s litem %s ritem %s",
                    lkey,
                    rkey,
                    litem,
                    ritem,
                )
                yield p

    def join(
        self, rel: JoinKeyRelation, rows: Optional[Iterator[JoinItemList]] = None
    ) -> Iterator[JoinItemList]:
        """
        Join the rows and the source with the relation.

        If no rows, join for all lines.
        """
        if rows is None:
            yield from self.__full_join(rel)
            return

        lkey, rkey = rel.left.add(-1, -1), rel.right.add(-1, -1)
        lindex, rindex = self.__get_index(lkey), self.__get_index(rkey)

        def as_item(x: Any) -> JoinItem:
            return cast(JoinItem, x)

        is_initial = True
        row_srcs: Optional[list[int]] = None
        for row in rows:
            debug("Join check: lkey %s rkey %s row %s", lkey, rkey, row)
            if is_initial:
                row_srcs = list(row.keys())
            elif list(row.keys()) != row_srcs:
                raise Exception(
                    f"Inconsistent columns, want {row_srcs}, got {list(row.keys())}"
                )

            match (row.get(lkey.src), row.get(rkey.src)):
                case (None, None):
                    pass
                case (lrow, None):
                    lrow = as_item(lrow)
                    lline = lindex.read(lrow.index).line
                    k = lindex.key(lline)
                    ritems = rindex.get(k)
                    if not ritems:
                        continue
                    for ritem in ritems:
                        r = row.copy()
                        r.set(JoinItem(src=rkey.src, index=ritem))
                        debug(
                            "Join: from lrow %s lline %s k %s ritem %s",
                            lrow,
                            lline,
                            k,
                            ritem,
                        )
                        yield r
                case (None, rrow):
                    rrow = as_item(rrow)
                    rline = rindex.read(rrow.index).line
                    k = rindex.key(rline)
                    litems = lindex.get(k)
                    if not litems:
                        continue
                    for litem in litems:
                        r = row.copy()
                        r.set(JoinItem(src=lkey.src, index=litem))
                        debug(
                            "Join: from rrow %s rline %s k %s litem %s",
                            rrow,
                            rline,
                            k,
                            litem,
                        )
                        yield r
                case (lrow, rrow):
                    lrow, rrow = as_item(lrow), as_item(rrow)
                    lline, rline = (
                        lindex.read(lrow.index).line,
                        rindex.read(rrow.index).line,
                    )
                    lk, rk = lindex.key(lline), rindex.key(rline)
                    debug(
                        "Join: by eq lrow %s rrow %s lline %s rline %s lk %s rk %s",
                        lrow,
                        rrow,
                        lline,
                        rline,
                        lk,
                        rk,
                    )
                    if lk == rk:
                        yield row


class Joiner:
    """Data source joiner."""

    def __init__(self, rel_joiner: RelationJoiner):
        """Return a new `Joiner`."""
        self.__rel_joiner = rel_joiner

    def join(self, join_key: JoinKey, dbg: bool = False) -> Iterator[JoinItemList]:
        """
        Join the sources.

        :join_key: join relations
        :dbg: enable debug
        """
        if len(join_key) == 0:
            raise ValidationException("Join key is empty")

        result: Iterator[JoinItemList] | None = None
        for i, key in enumerate(join_key):
            result = self.__rel_joiner.join(key, result)
            if dbg:
                n = i + 1
                r = list(result)
                debug("Joined: [%d] result len = %d", n, len(r))
                for x in r:
                    debug("Joined: [%d] %s %s", n, key, x)
                result = iter(r)
        yield from cast(Iterator[JoinItemList], result)


@with_debug
def select_columns(target: Target, column_list: list[list[str]]) -> list[str]:
    """Select columns from column_list via target."""

    def in_src_range(src: int) -> bool:
        return 0 <= src < len(column_list)

    @with_debug
    def select(rng: Range) -> list[str]:
        l, r = rng.ends()
        if not (in_src_range(l.src) and in_src_range(r.src - 1)):
            raise Exception(
                f"Out of source range: {rng} not in [0, {len(column_list)}]"
            )

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


class Selector:
    """Select columns and join them."""

    def __init__(self, target: Target, srcs: Sequence[TextIO], delimiter: str):
        """
        Return a new `Selector`.

        :target: columns to select
        :srcs: data sources
        :delimiter: column delimiter
        """
        self.__target = target
        self.__delimiter = delimiter
        self.__srcs = srcs

    def __read(self, src: int, offset: int) -> str:
        data = self.__srcs[src]
        data.seek(offset)
        return data.readline().rstrip()

    def select(self, items: JoinItemList) -> str:
        """Select columns and join them."""
        lines = (self.__read(item.src, item.index.offset) for item in items.items())
        return self.__delimiter.join(
            select_columns(self.__target, [x.split(self.__delimiter) for x in lines])
        )


@dataclass
class Arguments:
    """
    Arguments of `Runner`.

    :sources: data sources
    :delimiter: column delimiter
    :joinkey: join spec
    :target: target expression
    """

    sources: Sequence[TextIO]
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
        if len(self.sources) < 2:
            raise ValidationException("Require multiple sources")
        return Runner(self)


@dataclass
class Runner:
    """Join data sources."""

    args: Arguments

    def run(self) -> Iterator[str]:
        """Run join."""
        joinkey = Parser.parse_joinkey(self.args.joinkey)
        target = Parser.parse_target(self.args.target)
        cache = IndexCache(self.args.sources)
        joiner = Joiner(RelationJoiner(cache, self.args.delimiter))
        selector = Selector(target, self.args.sources, self.args.delimiter)
        for items in joiner.join(joinkey):
            yield selector.select(items)
