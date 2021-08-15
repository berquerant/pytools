"""Common parts."""


import json
from io import TextIOBase
from os import path
from typing import Any, Iterator, Optional, Union


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


def json_dumps(obj: Any, compact=True, sort_keys=False) -> str:
    """Serialize obj as JSON."""
    if compact:
        return json.dumps(obj, separators=(",", ":"), sort_keys=sort_keys)
    return json.dumps(obj, sort_keys=sort_keys)


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
