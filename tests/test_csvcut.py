from typing import List

import pytest

import pytools.csvcut as csvcut


@pytest.mark.parametrize(
    "title,target,row,want",
    [
        (
            "empty row",
            csvcut.Target([csvcut.Range(0)]),
            [],
            [],
        ),
        (
            "no ranges",
            csvcut.Target([]),
            ["the", "quick", "brown", "fox", "jumps", "over", "the", "lazy", "dog"],
            [],
        ),
        (
            "select a column",
            csvcut.Target([csvcut.Range(1, 1)]),
            ["the", "quick", "brown", "fox", "jumps", "over", "the", "lazy", "dog"],
            ["the"],
        ),
        (
            "select closed range",
            csvcut.Target([csvcut.Range(1, 3)]),
            ["the", "quick", "brown", "fox", "jumps", "over", "the", "lazy", "dog"],
            ["the", "quick", "brown"],
        ),
        (
            "select open range upper",
            csvcut.Target([csvcut.Range(7)]),
            ["the", "quick", "brown", "fox", "jumps", "over", "the", "lazy", "dog"],
            ["the", "lazy", "dog"],
        ),
        (
            "select open range lower",
            csvcut.Target([csvcut.Range(end=3)]),
            ["the", "quick", "brown", "fox", "jumps", "over", "the", "lazy", "dog"],
            ["the", "quick", "brown"],
        ),
        (
            "concat ranges",
            csvcut.Target([csvcut.Range(end=3), csvcut.Range(5, 5)]),
            ["the", "quick", "brown", "fox", "jumps", "over", "the", "lazy", "dog"],
            ["the", "quick", "brown", "jumps"],
        ),
        (
            "concat ranges overlapped",
            csvcut.Target([csvcut.Range(6), csvcut.Range(4, 7)]),
            ["the", "quick", "brown", "fox", "jumps", "over", "the", "lazy", "dog"],
            ["over", "the", "lazy", "dog", "fox", "jumps", "over", "the"],
        ),
    ],
)
def test_target(title: str, target: csvcut.Target, row: List[str], want: List[str]):
    assert want == target.select(row)
