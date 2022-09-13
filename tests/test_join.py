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


def test_parse_joinkey():
    got = join.Parser.parse_joinkey("1.2=2.3")
    want = join.Interval(join.Location(src=1, col=2), join.Location(src=2, col=3))
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
    got = index.get(key)
    assert want == got


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


TestJoinList = [
    ["apple,mela", "apple,りんご"],
    ["stone,pietra", "stone,石"],
    ["waterfall,cascata", "滝,waterfall"],
]


@pytest.mark.parametrize(
    "title,key,want",
    [
        (
            "join left and left",
            join.JoinKey(join.Location(1, 1), join.Location(2, 1)),
            [
                "apple,mela,apple,りんご",
                "stone,pietra,stone,石",
            ],
        ),
        (
            "join left and left reverse",
            join.JoinKey(join.Location(2, 1), join.Location(1, 1)),
            [
                "apple,mela,apple,りんご",
                "stone,pietra,stone,石",
            ],
        ),
        (
            "join left and right",
            join.JoinKey(join.Location(1, 1), join.Location(2, 2)),
            [
                "waterfall,cascata,滝,waterfall",
            ],
        ),
    ],
)
def test_join(title: str, key: join.JoinKey, want: list[str]):
    got = join.Joiner(
        StringIO("\n".join(x[0] for x in TestJoinList)),
        StringIO("\n".join(x[1] for x in TestJoinList)),
    ).join(key, ",", [join.Left(join.Location(1, 1)), join.Left(join.Location(2, 1))])
    assert want == list(got)
