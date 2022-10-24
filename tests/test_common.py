import io
from textwrap import dedent
from typing import Any, List, Optional

import pytest

import pytools.common as common


@pytest.mark.parametrize(
    "title,headers,delimiter,rows,want",
    [
        (
            "no headers empty list",
            None,
            ",",
            [],
            [],
        ),
        (
            "no headers 1 row",
            None,
            ",",
            [[1, "top"]],
            ["1,top"],
        ),
        (
            "only headers",
            ["id", "category"],
            ",",
            [],
            [],
        ),
        (
            "with headers",
            ["id", "category"],
            ",",
            [{"id": 1, "category": "paper"}],
            [
                "id,category",
                "1,paper",
            ],
        ),
        (
            "change delimiter",
            ["id", "category"],
            "|",
            [{"id": 1, "category": "paper"}],
            [
                "id|category",
                "1|paper",
            ],
        ),
        (
            "limit columns with headers",
            ["id", "category"],
            ",",
            [{"id": 1, "category": "paper", "desc": "other"}],
            [
                "id,category",
                "1,paper",
            ],
        ),
    ],
)
def test_csv_writer(
    title: str,
    headers: Optional[List[str]],
    delimiter: str,
    rows: List[Any],
    want: List[str],
):
    buf = io.StringIO()
    w = common.CSVWriter(buf, headers, delimiter)
    for r in rows:
        w.write(r)
    got = buf.getvalue().splitlines()
    assert got == want, got


def test_csv_writer_consistent_row():
    buf = io.StringIO()
    w = common.CSVWriter(buf, ["a", "b"], ",", True)
    rows = [
        {"a": 1, "b": 2},
        {"a": 2, "b": 3},
    ]
    want = [
        "a,b",
        "1,2",
        "2,3",
    ]
    for r in rows:
        w.write(r)
    got = buf.getvalue().splitlines()
    assert got == want, got


@pytest.mark.parametrize(
    "headers,rows",
    [
        (
            ["a", "b"],
            [
                {"a": 1, "b": 2},
                {"a": 1},
            ],
        ),
        (
            ["a", "b"],
            [
                {"a": 1, "b": 2},
                {"a": 1, "b": 3, "c": 5},
            ],
        ),
    ],
)
def test_csv_writer_inconsistent_row(headers: List[str], rows: List[Any]):
    buf = io.StringIO()
    w = common.CSVWriter(buf, headers, ",", True)
    with pytest.raises(
        common.ValidationException, match=r"^Inconsistent headers found"
    ):
        for r in rows:
            w.write(r)


@pytest.mark.parametrize(
    "headers,rows",
    [
        (
            ["a", "b"],
            [
                {"a": 1, "b": 2},
                {"a": 2},
            ],
        ),
        (
            ["a", "b"],
            [
                {"a": 1, "b": 2},
                {"a": 2, "b": 3, "c": 4},
            ],
        ),
        (
            ["a", "b"],
            [
                [1, 2],
                [3],
            ],
        ),
        (
            ["a", "b"],
            [
                [1, 2],
                [3, 4, 5],
            ],
        ),
    ],
)
def test_json_writer_inconsistent_row(headers: List[str], rows: List[Any]):
    buf = io.StringIO()
    w = common.JSONWriter(buf, headers, True)
    with pytest.raises(
        common.ValidationException, match=r"^Inconsistent headers found"
    ):
        for r in rows:
            w.write(r)


@pytest.mark.parametrize(
    "headers,rows,want",
    [
        (
            ["a", "b"],
            [
                {"a": 1, "b": 2},
                {"a": 3, "b": 4},
            ],
            dedent(
                """\
            {"a":1,"b":2}
            {"a":3,"b":4}
            """
            ),
        ),
        (
            ["a", "b"],
            [
                [1, 2],
                [3, 4],
            ],
            dedent(
                """\
            {"a":1,"b":2}
            {"a":3,"b":4}
            """
            ),
        ),
    ],
)
def test_json_writer_consistent_row(headers: List[str], rows: List[Any], want: str):
    buf = io.StringIO()
    w = common.JSONWriter(buf, headers, True)
    for r in rows:
        w.write(r)
    got = buf.getvalue()
    assert got == want, got


@pytest.mark.parametrize(
    "title,headers,rows,want",
    [
        (
            "no headers empty list",
            None,
            [[]],
            "[]\n",
        ),
        (
            "no headers",
            None,
            [[1, "story"], [3, "sky"]],
            """[1,"story"]
[3,"sky"]
""",
        ),
        (
            "with headers empty list",
            ["id", "unit"],
            [[]],
            "{}\n",
        ),
        (
            "with headers",
            ["id", "unit"],
            [[1, "story"], [3, "sky"], [5]],
            """{"id":1,"unit":"story"}
{"id":3,"unit":"sky"}
{"id":5}
""",
        ),
    ],
)
def test_json_writer(
    title: str, headers: Optional[List[str]], rows: List[List[Any]], want: str
):
    buf = io.StringIO()
    w = common.JSONWriter(buf, headers)
    for r in rows:
        w.write(r)
    got = buf.getvalue()
    assert got == want, got
