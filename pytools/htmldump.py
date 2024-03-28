"""HTMLDump command."""

from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass
from html.parser import HTMLParser
from io import TextIOBase
from queue import Empty, Queue
from threading import Event, Thread
from typing import Iterator, Union

from .common import json_dumps, textiter


class HTMLDumper(HTMLParser, ABC):
    """Dump html as stream."""

    q: Queue

    def __init__(self, q: Queue):  # noqa
        super().__init__(convert_charrefs=True)
        self.q = q

    @abstractmethod
    def translate_data(self, x: str):
        """Translate data, text, comment, etc..."""

    @abstractmethod
    def translate_attrs(self, attrs: list):
        """Translate attributions."""

    @abstractmethod
    def log(self, x: dict) -> str:
        """Translate log before enqueue."""

    def put(self, x: dict):
        """Put log into queue."""
        self.q.put(self.log(x))

    @staticmethod
    def gen_log(kind: str) -> OrderedDict:
        """Generate a seed of log."""
        return OrderedDict(kind=kind)

    def handle_starttag(self, tag: str, attrs: list):  # noqa
        d = self.gen_log("start_tag")
        d["tag"] = tag
        d["attrs"] = self.translate_attrs(attrs)
        self.put(d)

    def handle_endtag(self, tag: str):  # noqa
        d = self.gen_log("end_tag")
        d["tag"] = tag
        self.put(d)

    def handle_startendtag(self, tag: str, attrs: list):  # noqa
        d = self.gen_log("startend_log")
        d["tag"] = tag
        d["attrs"] = self.translate_attrs(attrs)
        self.put(d)

    def handle_data(self, data: str):  # noqa
        d = self.gen_log("data")
        d["data"] = self.translate_data(data)
        self.put(d)

    def handle_comment(self, data: str):  # noqa
        d = self.gen_log("comment")
        d["data"] = self.translate_data(data)
        self.put(d)

    def handle_decl(self, decl: str):  # noqa
        d = self.gen_log("decl")
        d["data"] = self.translate_data(decl)
        self.put(d)

    def handle_pi(self, data: str):  # noqa
        d = self.gen_log("pi")
        d["data"] = self.translate_data(data)
        self.put(d)

    def unknown_decl(self, data: str):  # noqa
        d = self.gen_log("unknown")
        d["data"] = self.translate_data(data)
        self.put(d)


class HTMLJSONDumper(HTMLDumper):
    """Dump html as json."""

    def translate_data(self, x: str):  # noqa
        return "\\n".join(x.splitlines())

    def translate_attrs(self, attrs: list):  # noqa
        return attrs

    def log(self, x: dict) -> str:  # noqa
        return json_dumps(x, sort_keys=False)


class HTMLTSVDumper(HTMLDumper):
    """Dump html as tsv."""

    def translate_data(self, x: str):  # noqa
        return "\\n".join(x.splitlines())

    def translate_attrs(self, attrs: list):  # noqa
        return json_dumps(attrs, sort_keys=False)

    def log(self, x: dict) -> str:  # noqa
        return "\t".join(str(v) for v in x.values())


@dataclass
class Arguments:
    """
    Arguments of `Runner`.

    :source: html strings.
    :as_json: yield json if True else tsv.
    """

    source: Union[TextIOBase, Iterator[str], str]
    as_json: bool = True

    def runner(self) -> "Runner":
        """Return a new `Runner`."""
        return Runner(self)


@dataclass
class Runner:
    """Dump html elements."""

    args: Arguments

    def __readiter(self) -> Iterator[str]:
        return textiter(self.args.source)

    def run(self) -> Iterator[str]:
        """Run htmldump."""
        is_done = Event()
        q: Queue = Queue()
        dumper = HTMLJSONDumper(q) if self.args.as_json else HTMLTSVDumper(q)
        it = self.__readiter()

        def reader():
            try:
                for line in it:
                    dumper.feed(line)
            finally:
                dumper.close()
                is_done.set()

        Thread(target=reader).start()

        while not (is_done.is_set() and q.empty()):
            try:
                x = q.get(timeout=0.5)
                yield x
                q.task_done()
            except Empty:
                pass
