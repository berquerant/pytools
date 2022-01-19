from typing import List

import pytest

import pytools.mapdiff as mapdiff


def test_run_invalid_delimiter():
    with pytest.raises(mapdiff.InvalidDelimiterError):
        r = mapdiff.Arguments(left=["left"], right=["right"], delimiter="id").runner()
        list(r.run())


def test_run_no_key():
    with pytest.raises(mapdiff.NoKeyError):
        r = mapdiff.Arguments(left=["left1 left2"], right=["right1"], key=1).runner()
        list(r.run())


def test_run_duplicated_key():
    with pytest.raises(mapdiff.DuplicatedKeyError):
        r = mapdiff.Arguments(left=["left1", "left1"], right=[]).runner()
        list(r.run())


@pytest.mark.parametrize(
    "title,args,want",
    [
        (
            "no input no diff",
            mapdiff.Arguments(left=[], right=[]),
            [],
        ),
        (
            "left has a key",
            mapdiff.Arguments(left=["k1"], right=[]),
            ["< k1"],
        ),
        (
            "left and right have a key",
            mapdiff.Arguments(left=["k1"], right=["k1"]),
            [],
        ),
        (
            "left and right have a key with no diff",
            mapdiff.Arguments(left=["k1"], right=["k1"], with_no_diff=True),
            ["k1"],
        ),
        (
            "right has an extra row",
            mapdiff.Arguments(
                left=[
                    "k1 v1",
                ],
                right=[
                    "k1 v1",
                    "k2 v2",
                ],
            ),
            ["> k2 v2"],
        ),
        (
            "change key",
            mapdiff.Arguments(
                left=[
                    "v11 k1 v12",
                ],
                right=[
                    "v21 k1 v22",
                ],
                key=1,
            ),
            [
                "<>< v11 k1 v12",
                "<>> v21 k1 v22",
            ],
        ),
        (
            "change delimiter",
            mapdiff.Arguments(
                left=[
                    "k1,v11,v12",
                ],
                right=[
                    "k1,v21,v22",
                ],
                delimiter=",",
            ),
            [
                "<>< k1,v11,v12",
                "<>> k1,v21,v22",
            ],
        ),
    ],
)
def test_run(title: str, args: mapdiff.Arguments, want: List[str]):
    got = list(args.runner().run())
    assert len(got) == len(want), got
    assert all(g == w for g, w in zip(sorted(got), sorted(want))), got
