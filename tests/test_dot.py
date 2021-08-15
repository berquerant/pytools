import json
from dataclasses import dataclass, field
from typing import List, Optional
from unittest.mock import patch

import pytest

import pytools.dot as dot
from pytools.common import ValidationException, json_dumps


@dataclass
class Node:
    name: str
    label: Optional[str] = None


@dataclass
class Edge:
    start: str
    end: str
    label: Optional[str] = None


@dataclass
class MockDigraphWrapper(dot.DigraphWrapper):
    nodes: List[Node] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)

    def edge(self, start: str, end: str, label: Optional[str] = None):
        self.edges.append(Edge(start, end, label))

    def node(self, name: str, label: Optional[str] = None):
        self.nodes.append(Node(name, label))


class MockNIDGenerator:
    count: int = -1

    @classmethod
    def new_nid(cls) -> str:
        cls.count += 1
        return "nid{}".format(cls.count)

    @classmethod
    def reset(cls):
        cls.count = -1


def test_jsontree_drawer_validate():
    with pytest.raises(ValidationException):
        dot.JSONTreeDrawer([]).draw(MockDigraphWrapper(), "[]")


@pytest.mark.parametrize(
    "title,children,src,want_nodes,want_edges",
    [
        (
            "a node",
            [],
            {"node": "X"},
            [
                Node("nid0", '{"node":"X"}'),
            ],
            [],
        ),
        (
            "an edge",
            [
                "e",
            ],
            {
                "n": "N1",
                "e": {
                    "n": "N2",
                },
            },
            [
                Node("nid0", '{"n":"N1"}'),
                Node("nid1", '{"n":"N2"}'),
            ],
            [
                Edge("nid0", "nid1", "e"),
            ],
        ),
        (
            "tree",
            [
                "l",
                "r",
            ],
            {
                "n": "N1",
                "l": {"n": "N2"},
                "r": {
                    "n": "N3",
                    "l": {
                        "n": "N4",
                    },
                },
            },
            [
                Node("nid0", '{"n":"N1"}'),
                Node("nid1", '{"n":"N2"}'),
                Node("nid2", '{"n":"N3"}'),
                Node("nid3", '{"n":"N4"}'),
            ],
            [
                Edge("nid0", "nid1", "l"),
                Edge("nid0", "nid2", "r"),
                Edge("nid2", "nid3", "l"),
            ],
        ),
    ],
)
@patch("pytools.dot.uuid4", side_effect=MockNIDGenerator.new_nid)
@patch("pytools.dot.json_dumps", side_effect=json_dumps)
def test_jsontree_drawer(
    mock_json_dumps,
    mock_uuid4,
    title: str,
    children: List[str],
    src: dict,
    want_nodes: List[Node],
    want_edges: List[Edge],
):
    MockNIDGenerator.reset()
    g = MockDigraphWrapper()
    dot.JSONTreeDrawer(children).draw(g, json.dumps(src))
    assert len(g.nodes) == len(want_nodes)
    assert all(g == w for g, w in zip(g.nodes, want_nodes)), g.nodes
    assert len(g.edges) == len(want_edges)
    assert all(g == w for g, w in zip(g.edges, want_edges)), g.edges


@pytest.mark.parametrize(
    "title,src,want_nodes,want_edges",
    [
        (
            "zero",
            [],
            [],
            [],
        ),
        (
            "a node",
            [
                "N",
            ],
            [
                Node("N", "N"),
            ],
            [],
        ),
        (
            "an edge",
            [
                "N,N",
            ],
            [
                Node("N", "N"),
            ],
            [
                Edge("N", "N"),
            ],
        ),
        (
            "cycle",
            [
                "A,B",
                "B,C",
                "C,A",
            ],
            [
                Node("A", "A"),
                Node("B", "B"),
                Node("C", "C"),
            ],
            [
                Edge("A", "B"),
                Edge("B", "C"),
                Edge("C", "A"),
            ],
        ),
    ],
)
def test_csv_drawer(
    title: str, src: List[str], want_nodes: List[Node], want_edges: List[Edge]
):
    g = MockDigraphWrapper()
    dot.CSVDrawer().draw(g, src)
    assert len(g.nodes) == len(want_nodes)
    assert all(g == w for g, w in zip(g.nodes, want_nodes)), g.nodes
    assert len(g.edges) == len(want_edges)
    assert all(g == w for g, w in zip(g.edges, want_edges)), g.edges


@pytest.mark.parametrize(
    "title,src,want_nodes,want_edges",
    [
        (
            "zero",
            [],
            [],
            [],
        ),
        (
            "a node",
            [
                {
                    "id": "N",
                },
            ],
            [
                Node("N", "N"),
            ],
            [],
        ),
        (
            "an edge",
            [
                {
                    "id": "N1",
                    "to": [
                        {
                            "id": "N2",
                        },
                    ],
                },
                {
                    "id": "N2",
                },
            ],
            [
                Node("N1", "N1"),
                Node("N2", "N2"),
            ],
            [
                Edge("N1", "N2"),
            ],
        ),
        (
            "cycle",
            [
                {
                    "id": "A",
                    "to": [
                        {
                            "id": "B",
                            "el": "ab",
                        },
                    ],
                },
                {
                    "id": "B",
                    "to": [
                        {
                            "id": "C",
                            "el": "bc",
                        },
                    ],
                },
                {
                    "id": "C",
                    "to": [
                        {
                            "id": "A",
                            "el": "ca",
                        },
                    ],
                },
            ],
            [
                Node("A", "A"),
                Node("B", "B"),
                Node("C", "C"),
            ],
            [
                Edge("A", "B", "ab"),
                Edge("B", "C", "bc"),
                Edge("C", "A", "ca"),
            ],
        ),
    ],
)
@patch("pytools.dot.json_dumps", side_effect=json_dumps)
def test_json_drawer(
    mock_json_dumps,
    title: str,
    src: List[dict],
    want_nodes: List[Node],
    want_edges: List[Edge],
):
    g = MockDigraphWrapper()
    dot.JSONDrawer().draw(g, [json.dumps(x) for x in src])
    assert len(g.nodes) == len(want_nodes)
    assert all(g == w for g, w in zip(g.nodes, want_nodes)), g.nodes
    assert len(g.edges) == len(want_edges)
    assert all(g == w for g, w in zip(g.edges, want_edges)), g.edges
