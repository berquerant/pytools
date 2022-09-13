"""Common parts."""

import csv
import json
from dataclasses import asdict, is_dataclass
from io import TextIOBase
from os import path
from typing import Any, Callable, Dict, Iterator, List, Optional, Protocol, Union


class BaseException(Exception):
    """Base exception class of pytools."""


class ValidationException(BaseException):
    """Exception for invalid arguments."""


def find_extension(filename: str) -> Optional[str]:
    """Find extension from filename.

    >>> from pytools import common
    >>> common.find_extension("~/crete/iraklion.u4")
    'u4'
    >>> common.find_extension("~/crete/iraklion") is None
    True
    """
    p = path.basename(path.abspath(filename)).split(".")
    if len(p) > 1:
        return p[-1]
    return None


JSONEncoder = Callable[[Any], Any]


def __json_dumps_default(encoder: Optional[JSONEncoder] = None) -> JSONEncoder:
    def inner(obj: Any) -> Any:
        if is_dataclass(obj):
            return asdict(obj)
        if encoder:
            return encoder(obj)
        raise TypeError()

    return inner


def json_dumps(
    obj: Any,
    compact: bool = True,
    sort_keys: bool = True,
    default: Optional[JSONEncoder] = None,
) -> str:
    """Serialize obj as JSON."""
    default_encoder = __json_dumps_default(default)
    if compact:
        return json.dumps(
            obj, separators=(",", ":"), sort_keys=sort_keys, default=default_encoder
        )
    return json.dumps(obj, sort_keys=sort_keys, default=default_encoder)


def textiter(obj: Union[str, Iterator[str], TextIOBase]) -> Iterator[str]:
    r"""Convert some types for str into iterator.

    >>> from pytools import common
    >>> list(common.textiter("string"))
    ['string']
    >>> list(common.textiter("mail.google.com".split(".")))
    ['mail', 'google', 'com']
    >>> from io import StringIO
    >>> list(common.textiter(StringIO("textio\nstringio\n")))
    ['textio\n', 'stringio\n']
    """
    if isinstance(obj, str):
        yield obj
        return
    if not isinstance(obj, TextIOBase):
        yield from obj
        return
    while True:
        line = obj.readline()
        if not line:
            return
        yield line


StructWriterRow = Union[List[Any], Dict[str, Any]]


class StructWriter(Protocol):
    """Structured log writer."""

    def write(self, row: StructWriterRow):
        """Write a row."""


class JSONWriter(StructWriter):
    """JSON log writer."""

    def __init__(self, dest: TextIOBase, headers: Optional[List[str]] = None):
        """Return a new JSONWriter."""
        super().__init__()
        self.dest = dest
        self.headers = headers

    def __new_row(self, row: StructWriterRow) -> Any:
        if not self.headers:
            return row
        if isinstance(row, dict):
            return {k: v for k, v in row.items() if k in self.headers}
        return dict(zip(self.headers, row))

    def write(self, row: StructWriterRow):  # noqa: D102
        print(json_dumps(self.__new_row(row)), file=self.dest)


class CSVWriter(StructWriter):
    """CSV log writer."""

    def __init__(
        self, dest: TextIOBase, headers: Optional[List[str]] = None, delimiter=","
    ):
        """Return a new CSVWriter."""
        super().__init__()
        self.writer = csv.writer(dest, delimiter=delimiter)
        self.headers = headers
        self.is_head = True

    def __write_csv(self, row: List[Any]):
        self.writer.writerow(row)

    def __write_headers(self):
        if self.headers:
            self.__write_csv(self.headers)

    def __new_row(self, row: StructWriterRow) -> List[Any]:
        if isinstance(row, list):
            return row
        if not self.headers:
            return [row[k] for k in sorted(row)]
        return [row[k] for k in self.headers if k in row]

    def write(self, row: StructWriterRow):  # noqa: D102
        if self.is_head:
            self.__write_headers()
            self.is_head = False
        self.__write_csv(self.__new_row(row))
