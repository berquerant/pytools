import io
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
