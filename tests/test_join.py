from io import StringIO
from typing import Optional

import pytest

import pytools.join as join


@pytest.mark.parametrize(
    "title,value,want",
    [
        (
            "single",
            "1.2",
            [join.Single(join.Location(src=1, col=2))],
        ),
        ("left", "2.1-", [join.Left(join.Location(src=2, col=1))]),
        ("right", "-3.2", [join.Right(join.Location(src=3, col=2))]),
        (
            "interval",
            "1.2-1.5",
            [join.Interval(join.Location(src=1, col=2), join.Location(src=1, col=5))],
        ),
        (
            "interval over src",
            "1.2-2.5",
            [join.Interval(join.Location(src=1, col=2), join.Location(src=2, col=5))],
        ),
        (
            "fuzz",
            "1.2,2.1-,-3.2,1.2-1.5,1.2-2.5",
            [
                join.Single(join.Location(src=1, col=2)),
                join.Left(join.Location(src=2, col=1)),
                join.Right(join.Location(src=3, col=2)),
                join.Interval(join.Location(src=1, col=2), join.Location(src=1, col=5)),
                join.Interval(join.Location(src=1, col=2), join.Location(src=2, col=5)),
            ],
        ),
    ],
)
def test_parse_target(title: str, value: str, want: join.Target):
    got = join.Parser.parse_target(value)
    assert want == got


@pytest.mark.parametrize(
    "title,value,want",
    [
        (
            "1 relation",
            "1.2=2.3",
            [join.Interval(join.Location(src=1, col=2), join.Location(src=2, col=3))],
        ),
        (
            "2 relations",
            "1.2=2.3,2.1=3.2",
            [
                join.Interval(join.Location(src=1, col=2), join.Location(src=2, col=3)),
                join.Interval(join.Location(src=2, col=1), join.Location(src=3, col=2)),
            ],
        ),
    ],
)
def test_parse_joinkey(title: str, value: str, want: join.JoinKey):
    got = join.Parser.parse_joinkey(value)
    assert want == got


TestDataForIndex = """k1 v1
k2 v2
k3 v3
k2 v4
"""


@pytest.mark.parametrize(
    "title,key,want",
    [
        ("miss", "", None),
        ("hit", "k1", ["k1 v1"]),
        ("2 hits", "k2", ["k2 v2", "k2 v4"]),
    ],
)
def test_index(title: str, key: str, want: Optional[list[str]]):
    src = StringIO(TestDataForIndex)
    index = join.Index.new(src, lambda x: x.split()[0])
    item = index.get(key)
    if not item:
        assert want is None
        return
    got = [index.read(x).line for x in item]
    assert want == got


def test_index_scenario():
    index = join.Index.new(StringIO(TestDataForIndex), lambda x: x.split()[0])
    items = list(index.scan())
    want_all_lines = """k1 v1
k2 v2
k2 v4
k3 v3"""
    assert want_all_lines == "\n".join(sorted(x.line for x in items))
    items = [index.read(x) for x in index.get("k3")]
    assert ["k3 v3"] == [x.line for x in items]
    index.delete(items[0].index)
    assert index.get("k3") is None


TestColumnList = [
    ["11", "12", "13"],  # row 1
    ["21", "22", "23"],  # row 2
    ["31", "32", "33"],  # row 3
]


@pytest.mark.parametrize(
    "title,target,want",
    [
        ("single column", [join.Single(join.Location(1, 1))], ["11"]),
        ("single left", [join.Left(join.Location(2, 2))], ["22", "23"]),
        ("single right", [join.Right(join.Location(3, 2))], ["31", "32"]),
        (
            "single interval",
            [join.Interval(join.Location(1, 1), join.Location(1, 2))],
            ["11", "12"],
        ),
        (
            "interval over rows",
            [join.Interval(join.Location(1, 2), join.Location(2, 2))],
            ["12", "13", "21", "22"],
        ),
        (
            "no gap rows",
            [join.Interval(join.Location(2, 2), join.Location(1, 2))],
            [],
        ),
        (
            "no gap columns",
            [join.Interval(join.Location(1, 3), join.Location(1, 2))],
            [],
        ),
        (
            "sum columns",
            [
                join.Single(join.Location(2, 1)),
                join.Single(join.Location(1, 2)),
                join.Single(join.Location(2, 1)),
            ],
            ["21", "12", "21"],
        ),
    ],
)
def test_select_columns(title: str, target: join.Target, want: list[str]):
    got = join.select_columns(target, TestColumnList)
    assert want == got


@pytest.mark.parametrize(
    "title,srcs,key,target,want",
    [
        (
            "single column",
            [
                ["a,b,c", "d,e,f"],
                ["p,x,y", "p,z,t"],
            ],
            join.JoinKeyRelation(join.Location(1, 1), join.Location(2, 1)),
            [join.Single(join.Location(1, 2))],
            ["x"],
        ),
        (
            "multiple colimns",
            [
                ["a,b,c", "d,e,f"],
                ["p,x,y", "p,z,t"],
            ],
            join.JoinKeyRelation(join.Location(1, 1), join.Location(2, 1)),
            [
                join.Single(join.Location(1, 2)),
                join.Single(join.Location(1, 3)),
                join.Single(join.Location(2, 2)),
            ],
            ["x,y,z"],
        ),
        (
            "multiple colimns duplicated",
            [
                ["a,b,c", "d,e,f"],
                ["p,x,y", "p,z,t"],
            ],
            join.JoinKeyRelation(join.Location(1, 1), join.Location(2, 1)),
            [
                join.Single(join.Location(1, 2)),
                join.Single(join.Location(1, 3)),
                join.Single(join.Location(2, 2)),
                join.Single(join.Location(2, 2)),
            ],
            ["x,y,z,z"],
        ),
        (
            "multiple rows",
            [
                ["11,12,13", "14,15,16"],
                ["21,22,23", "11,25,26"],
                ["31,32,33", "11,35,36"],
                ["14,42,43", "44,45,46"],
            ],
            join.JoinKeyRelation(join.Location(1, 1), join.Location(2, 1)),
            [
                join.Single(join.Location(1, 1)),
                join.Single(join.Location(1, 3)),
                join.Single(join.Location(2, 3)),
            ],
            [
                "11,13,26",
                "11,13,36",
                "14,43,16",
            ],
        ),
    ],
)
def test_relation_joiner_full(
    title: str,
    srcs: list[list[str]],
    key: join.JoinKeyRelation,
    target: join.Target,
    want: list[str],
):
    data = [StringIO("\n".join(x[i] for x in srcs)) for i in range(len(srcs[0]))]
    rel = join.RelationJoiner(join.IndexCache(data), ",")
    sel = join.Selector(target, data, ",")
    got = [sel.select(x) for x in rel.join(key)]
    assert got == want


@pytest.mark.parametrize(
    "title,srcs,key,target,want",
    [
        (
            "single column",
            [
                ["a,b,c", "d,e,f"],
                ["p,x,y", "p,z,t"],
            ],
            [join.JoinKeyRelation(join.Location(1, 1), join.Location(2, 1))],
            [join.Single(join.Location(1, 2))],
            ["x"],
        ),
        (
            "duplicated key",
            [
                ["a,b,c", "d,e,f"],
                ["p,x,y", "p,z,t"],
            ],
            [
                join.JoinKeyRelation(join.Location(1, 1), join.Location(2, 1)),
                join.JoinKeyRelation(join.Location(1, 1), join.Location(2, 1)),
            ],
            [join.Single(join.Location(1, 2))],
            ["x"],
        ),
        (
            "2 joins",
            [
                ["a,b,c", "d,e,f", "p,q,r"],
                ["p,x,y", "p,z,t", "p,q2,r2"],
            ],
            [
                join.JoinKeyRelation(join.Location(1, 1), join.Location(2, 1)),
                join.JoinKeyRelation(join.Location(2, 1), join.Location(3, 1)),
            ],
            [join.Single(join.Location(1, 2)), join.Single(join.Location(3, 2))],
            [
                "x,q",
                "x,q2",
            ],
        ),
        (
            "2 joins multiple",
            [
                ["11,12", "13,14", "15,16,17"],
                ["21,22", "11,24", "25,26,27"],
                ["31,32", "21,34", "11,36,37"],
                ["41,42", "43,44", "11,46,47"],
                ["11,52", "53,54", "55,56,57"],
            ],
            [
                join.JoinKeyRelation(join.Location(1, 1), join.Location(2, 1)),
                join.JoinKeyRelation(join.Location(2, 1), join.Location(3, 1)),
            ],
            [
                join.Single(join.Location(1, 2)),
                join.Single(join.Location(2, 2)),
                join.Single(join.Location(3, 2)),
            ],
            [
                "12,24,36",
                "12,24,46",
                "52,24,36",
                "52,24,46",
            ],
        ),
        (
            "3 joins",
            [
                ["11,12", "13,14", "15,16,17", "18,19"],
                ["21,22", "11,24", "25,26,27", "11,29"],
                ["31,32", "21,34", "11,36,37", "38,39"],
                ["41,42", "43,44", "11,46,47", "48,49"],
                ["11,52", "53,54", "55,56,57", "58,59"],
            ],
            [
                join.JoinKeyRelation(join.Location(1, 1), join.Location(2, 1)),
                join.JoinKeyRelation(join.Location(2, 1), join.Location(3, 1)),
                join.JoinKeyRelation(join.Location(1, 1), join.Location(4, 1)),
            ],
            [
                join.Single(join.Location(1, 2)),
                join.Single(join.Location(2, 2)),
                join.Single(join.Location(3, 2)),
                join.Single(join.Location(4, 2)),
            ],
            [
                "12,24,36,29",
                "12,24,46,29",
                "52,24,36,29",
                "52,24,46,29",
            ],
        ),
        (
            "3 joins with internal join",
            [
                ["11,12", "13,14", "15,16,17"],
                ["21,22", "11,11", "25,26,27"],
                ["31,32", "21,34", "11,36,37"],
                ["41,42", "43,44", "11,46,47"],
                ["11,52", "53,54", "55,56,57"],
            ],
            [
                join.JoinKeyRelation(join.Location(1, 1), join.Location(2, 1)),
                join.JoinKeyRelation(join.Location(2, 1), join.Location(3, 1)),
                join.JoinKeyRelation(join.Location(2, 2), join.Location(1, 1)),
            ],
            [
                join.Single(join.Location(1, 2)),
                join.Single(join.Location(2, 2)),
                join.Single(join.Location(3, 2)),
            ],
            [
                "12,11,36",
                "12,11,46",
                "52,11,36",
                "52,11,46",
            ],
        ),
    ],
)
def test_joiner(
    title: str,
    srcs: list[list[str]],
    key: join.JoinKey,
    target: join.Target,
    want: list[str],
):
    data = [StringIO("\n".join(x[i] for x in srcs)) for i in range(len(srcs[0]))]
    rel = join.RelationJoiner(join.IndexCache(data), ",")
    joiner = join.Joiner(rel)
    sel = join.Selector(target, data, ",")
    got = [sel.select(x) for x in joiner.join(key, dbg=True)]
    assert got == want
