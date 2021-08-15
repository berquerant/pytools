"""Dot command."""


import csv
import json
from dataclasses import dataclass
from io import TextIOBase
from os import path
from typing import Any, Iterator, List, Optional, Protocol, Union
from uuid import uuid4

from graphviz import Digraph

from .common import ValidationException, find_extension, textiter


def json_dumps(obj: Any) -> str:
    """Dump obj for node label."""
    return (
        json.dumps(obj, sort_keys=True, indent=" ")
        .replace("\n", "\\l")
        .replace("{", "\\{")
        .replace("}", "\\}")
        + "\\l"
    )


Source = Union[str, Iterator[str], TextIOBase]


@dataclass
class DigraphWrapper:
    """Wrap `graphviz.Digraph`."""

    g: Optional[Digraph] = None  # must exist, None for test

    def graph(self) -> Digraph:
        """Return the wrapped Digraph."""
        assert self.g is not None
        return self.g

    def edge(self, start: str, end: str, label: Optional[str] = None):
        """Add an edge."""
        self.graph().edge(start, end, label=label)

    def node(self, name: str, label: Optional[str] = None):
        """Add a node."""
        self.graph().node(name, label=label)


class Drawer(Protocol):
    """Draw graph content protocol."""

    def draw(self, g: DigraphWrapper, src: Source):
        """Draw graph content."""


class JSONDrawer(Drawer):  # noqa: D209
    """Draw digraph from json.

    example json:
    {"id":"A","to":[{"id":"B","el":"ab"}],"comment":"Alpha"}
    {"id":"B","to":[{"id":"C","el":"bc"}]}
    {"id":"C","to":[{"id":"A","el":"ca"},{"id":"C","el":"cc"}]}"""

    @dataclass
    class Dest:  # noqa
        id: str
        el: Optional[str] = None

    @dataclass
    class Row:  # noqa
        id: str
        to: list  # list of Dest
        desc: Optional[dict] = None

    @dataclass
    class Edge:  # noqa
        start: str
        end: str
        label: Optional[str] = None

    @classmethod
    def __read(cls, src: Source) -> Iterator[Row]:
        for line in textiter(src):
            j = json.loads(line)
            id = j["id"]
            del j["id"]
            to = j.get("to", [])
            if "to" in j:
                del j["to"]
            to = [cls.Dest(x["id"], x.get("el")) for x in to]
            yield cls.Row(id, to, j if j else None)

    def draw(self, g: DigraphWrapper, src: Source):  # noqa
        nids = set()
        edges = []
        for r in self.__read(src):
            if r.id not in nids:
                nids.add(r.id)
                g.node(
                    r.id, label=json_dumps({"id": r.id, **r.desc}) if r.desc else r.id
                )
            for t in r.to:
                edges.append(self.Edge(r.id, t.id, t.el))
        for e in edges:
            if e.end not in nids:  # in case the node is not declared
                nids.add(e.end)
                g.node(e.end, label=json_dumps({"id": e.end}))
            g.edge(e.start, e.end, e.label)


@dataclass
class JSONTreeDrawer(Drawer):
    """
    Draw digraph from json tree.

    example json tree:
    {"n":"N1","l":{"n":"N2"},"r":{"n":"N3","l":{"n":"N4"}}}
    """

    children: List[str]

    @staticmethod
    def __new_nid() -> str:
        return str(uuid4())

    def __draw(
        self,
        g: DigraphWrapper,
        x: Any,
        nid: str,
        edge_name: Optional[str] = None,
        parent_id: Optional[str] = None,
    ):
        if not isinstance(x, dict):
            g.node(nid, label=json_dumps(x))
            if parent_id:
                g.edge(parent_id, nid, label=edge_name)
            return

        children = {k: v for k, v in x.items() if k in self.children}
        for k in children.keys():
            del x[k]
        g.node(nid, label=json_dumps(x))
        if parent_id:
            g.edge(parent_id, nid, label=edge_name)
        for k in sorted(children.keys()):
            self.__draw(g, children[k], self.__new_nid(), k, nid)

    def draw(self, g: DigraphWrapper, src: Source):  # noqa
        root = json.loads("".join(textiter(src)))
        if not isinstance(root, dict):
            raise ValidationException("root must be object")
        self.__draw(g, root, self.__new_nid())


class CSVDrawer(Drawer):
    """
    Draw digraph from csv.

    exmaple csv:
    A,B
    B,C
    C,A,C
    """

    @dataclass
    class Row:  # noqa
        parent: str
        children: List[str]

    @classmethod
    def __read(cls, src: Source) -> Iterator["Row"]:
        for x in csv.reader(textiter(src)):
            yield cls.Row(parent=x[0], children=x[1:])

    def draw(self, g: DigraphWrapper, src: Source):  # noqa
        nids = set()

        def new_node(nid: str):
            if nid in nids:
                return
            nids.add(nid)
            g.node(nid, label=nid)

        for r in self.__read(src):
            new_node(r.parent)
            for c in r.children:
                new_node(c)
                g.edge(r.parent, c)


@dataclass
class Arguments:
    """
    Arguments of `Runner`.

    :source: source string.
    :destination: filename for saving image.
    :drawer: way of drawing image.
    """

    source: Source
    destination: str
    drawer: Drawer

    def runner(self) -> "Runner":
        """Return a new `Runner`."""
        return Runner(self)


@dataclass
class Runner:
    """Render graph."""

    args: Arguments

    def __new_graph(self) -> DigraphWrapper:
        return DigraphWrapper(
            Digraph(
                format=find_extension(self.args.destination),
                node_attr={
                    "shape": "plaintext",
                    "style": "solid,filled",
                    "width": "1",
                    "fontname": "arial",
                },
            )
        )

    def run(self) -> str:
        """Run dot."""
        g = self.__new_graph()
        self.args.drawer.draw(g, self.args.source)
        p = path.abspath(self.args.destination)
        fs = path.basename(p).split(".")
        f = ".".join(fs[: len(fs) - 1])
        g.graph().render(directory=path.dirname(p), filename=f)
        return p
